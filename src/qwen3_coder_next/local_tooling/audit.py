"""Audit logging abstractions for the local tooling layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qwen3_coder_next.local_tooling.contracts import AuditRecord


class AuditLoggerErrorCode(StrEnum):
    """Structured error codes for audit logging operations."""

    EVENT_NOT_FOUND = "event_not_found"
    INVALID_RECORD = "invalid_record"
    SCHEMA_MISMATCH = "schema_mismatch"
    APPEND_FAILED = "append_failed"
    PERSISTENCE_FAILED = "persistence_failed"


class AuditLoggerError(Exception):
    """Structured audit logger error with a stable error code."""

    def __init__(
        self,
        error_code: AuditLoggerErrorCode,
        message: str,
        *,
        request_id: str | None = None,
        event_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.request_id = request_id
        self.event_id = event_id


@dataclass(frozen=True, slots=True)
class AuditLoggerRequest:
    """Immutable request for appending an audit record."""

    request_id: str
    action: str
    subject: str
    status: str
    details: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AuditLoggerResult:
    """Immutable result returned by an audit logger."""

    request_id: str
    record: AuditRecord | None
    success: bool
    error_code: AuditLoggerErrorCode | None = None
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class AuditLogger(ABC):
    """Abstract audit logger interface."""

    @abstractmethod
    def append(self, request: AuditLoggerRequest) -> AuditLoggerResult:
        """Append a new audit record."""

    @abstractmethod
    def list(self) -> list[AuditRecord]:
        """Return all audit records in deterministic order."""

    @abstractmethod
    def get(self, event_id: str) -> AuditRecord:
        """Return an audit record by event identifier."""

    @abstractmethod
    def history(self, request_id: str) -> list[AuditRecord]:
        """Return all audit records for a request identifier."""


class DeterministicAuditLogger(AuditLogger):
    """Deterministic JSON-backed append-only audit logger."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self._storage_path = storage_path
        self._records: list[AuditRecord] = []
        self._sequence_number = 0
        self._load_error: AuditLoggerError | None = None
        self._load()

    def append(self, request: AuditLoggerRequest) -> AuditLoggerResult:
        """Append a new immutable audit record."""

        if self._load_error is not None:
            return self._reject(
                request.request_id,
                self._load_error.error_code,
                str(self._load_error),
                request.metadata,
            )
        if not isinstance(request.action, str) or not request.action.strip():
            return self._reject(
                request.request_id,
                AuditLoggerErrorCode.INVALID_RECORD,
                "Audit action must be a non-empty string.",
                request.metadata,
            )
        if not isinstance(request.subject, str) or not request.subject.strip():
            return self._reject(
                request.request_id,
                AuditLoggerErrorCode.INVALID_RECORD,
                "Audit subject must be a non-empty string.",
                request.metadata,
            )
        previous_records = list(self._records)
        previous_sequence_number = self._sequence_number
        self._sequence_number += 1
        record = AuditRecord(
            event_id=f"event-{self._sequence_number:08d}",
            sequence_number=self._sequence_number,
            request_id=request.request_id,
            timestamp=datetime.now(UTC),
            action=request.action,
            subject=request.subject,
            status=request.status,
            details=request.details,
            metadata=request.metadata,
        )
        self._records.append(record)
        save_error = self._save()
        if save_error is not None:
            self._records = previous_records
            self._sequence_number = previous_sequence_number
            return self._reject(request.request_id, save_error.error_code, str(save_error), request.metadata)
        return AuditLoggerResult(request_id=request.request_id, record=record, success=True, metadata=request.metadata)

    def list(self) -> list[AuditRecord]:
        """Return records in append order."""

        if self._load_error is not None:
            raise self._load_error
        return list(self._records)

    def get(self, event_id: str) -> AuditRecord:
        """Return a record by event identifier."""

        if self._load_error is not None:
            raise self._load_error
        for record in self._records:
            if record.event_id == event_id:
                return record
        raise AuditLoggerError(
            AuditLoggerErrorCode.EVENT_NOT_FOUND,
            f"Audit event not found for event_id={event_id!r}.",
            event_id=event_id,
        )

    def history(self, request_id: str) -> list[AuditRecord]:
        """Return all audit records for a request identifier."""

        if self._load_error is not None:
            raise self._load_error
        return [record for record in self._records if record.request_id == request_id]

    def _reject(
        self,
        request_id: str,
        error_code: AuditLoggerErrorCode,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLoggerResult:
        return AuditLoggerResult(
            request_id=request_id,
            record=None,
            success=False,
            error_code=error_code,
            error_message=message,
            metadata=metadata or {},
        )

    def _load(self) -> None:
        if self._storage_path is None or not self._storage_path.exists():
            return
        import json

        try:
            with self._storage_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, list):
                raise AuditLoggerError(
                    AuditLoggerErrorCode.SCHEMA_MISMATCH,
                    "Persisted audit payload must be a list of records.",
                )
            self._records = [self._deserialize_record(item) for item in payload]
            self._sequence_number = max((record.sequence_number for record in self._records), default=0)
        except AuditLoggerError as error:
            self._records = []
            self._sequence_number = 0
            self._load_error = error
        except (OSError, ValueError, TypeError) as error:
            self._records = []
            self._sequence_number = 0
            self._load_error = AuditLoggerError(
                AuditLoggerErrorCode.PERSISTENCE_FAILED,
                f"Failed to load audit log: {error}.",
            )

    def _save(self) -> AuditLoggerError | None:
        if self._storage_path is None:
            return None
        import json

        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            with self._storage_path.open("w", encoding="utf-8") as handle:
                json.dump([self._serialize_record(item) for item in self.list()], handle, indent=2)
        except OSError as error:
            return AuditLoggerError(
                AuditLoggerErrorCode.APPEND_FAILED,
                f"Failed to append audit record: {error}.",
            )
        return None

    def _serialize_record(self, record: AuditRecord) -> dict[str, object]:
        return {
            "event_id": record.event_id,
            "sequence_number": record.sequence_number,
            "request_id": record.request_id,
            "timestamp": record.timestamp.isoformat(),
            "action": record.action,
            "subject": record.subject,
            "status": record.status,
            "details": record.details,
            "metadata": record.metadata,
        }

    def _deserialize_record(self, payload: dict[str, object]) -> AuditRecord:
        if not isinstance(payload, dict):
            raise AuditLoggerError(
                AuditLoggerErrorCode.SCHEMA_MISMATCH,
                "Persisted audit record payload must be a mapping.",
            )
        required_keys = (
            "event_id",
            "sequence_number",
            "request_id",
            "timestamp",
            "action",
            "subject",
            "status",
        )
        if any(key not in payload for key in required_keys):
            raise AuditLoggerError(
                AuditLoggerErrorCode.SCHEMA_MISMATCH,
                "Persisted audit record payload is missing required fields.",
            )
        return AuditRecord(
            event_id=str(payload["event_id"]),
            sequence_number=int(payload["sequence_number"]),
            request_id=str(payload["request_id"]),
            timestamp=datetime.fromisoformat(str(payload["timestamp"])),
            action=str(payload["action"]),
            subject=str(payload["subject"]),
            status=str(payload["status"]),
            details=dict(payload.get("details", {})),
            metadata=dict(payload.get("metadata", {})),
        )
