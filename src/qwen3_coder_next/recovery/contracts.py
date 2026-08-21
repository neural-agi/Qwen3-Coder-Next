"""Versioned, serializable contracts for the recovery control plane."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

RECOVERY_SCHEMA_VERSION = 1


class FailureCategory(StrEnum):
    """Controlled failure taxonomy used by later diagnosis stages."""

    TRANSIENT = "transient"
    SEMANTIC = "semantic"
    ENVIRONMENTAL = "environmental"
    UNRECOVERABLE = "unrecoverable"
    UNKNOWN = "unknown"


class Severity(StrEnum):
    """Normalized failure severity."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryStrategy(StrEnum):
    """Bounded strategies available to later recovery policy stages."""

    RETRY_SAME = "retry_same"
    RETRY_WITH_CONTEXT = "retry_with_context"
    DECOMPOSE = "decompose"
    ALTERNATIVE_APPROACH = "alternative_approach"
    ESCALATE = "escalate"
    ABORT = "abort"


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text.")
    return value.strip()


def _texts(value: object, name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must be a collection of text.")
    try:
        result = tuple(value or ())  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValueError(f"{name} must be a collection of text.") from exc
    if any(not isinstance(item, str) or not item.strip() for item in result):
        raise ValueError(f"{name} contains invalid text.")
    return tuple(item.strip() for item in result)


@dataclass(frozen=True, slots=True)
class FailureEvent:
    """Normalized failure signal received from another subsystem."""

    task_id: str
    source_agent: str
    failure_type: str
    severity: Severity
    message: str
    timestamp: str
    stack_trace_ref: str = ""
    tool_ref: str = ""
    retry_count: int = 0
    worktree_ref: str = ""
    raw_payload: str = ""
    schema_version: int = RECOVERY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("task_id", "source_agent", "failure_type", "message", "timestamp"):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        if not isinstance(self.severity, Severity):
            try:
                object.__setattr__(self, "severity", Severity(self.severity))
            except (TypeError, ValueError) as exc:
                raise ValueError("severity is invalid.") from exc
        if not isinstance(self.retry_count, int) or self.retry_count < 0:
            raise ValueError("retry_count must be a non-negative integer.")
        for name in ("stack_trace_ref", "tool_ref", "worktree_ref", "raw_payload"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise ValueError(f"{name} must be text.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "source_agent": self.source_agent,
            "failure_type": self.failure_type,
            "severity": self.severity.value,
            "message": self.message,
            "stack_trace_ref": self.stack_trace_ref,
            "tool_ref": self.tool_ref,
            "timestamp": self.timestamp,
            "retry_count": self.retry_count,
            "worktree_ref": self.worktree_ref,
            "raw_payload": self.raw_payload,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    """Evidence references captured for a failure, without collection logic."""

    recent_actions: tuple[str, ...] = ()
    log_refs: tuple[str, ...] = ()
    command_output: tuple[str, ...] = ()
    memory_refs: tuple[str, ...] = ()
    file_anchors: tuple[str, ...] = ()
    worktree_ref: str = ""
    schema_version: int = RECOVERY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("recent_actions", "log_refs", "command_output", "memory_refs", "file_anchors"):
            object.__setattr__(self, name, _texts(getattr(self, name), name))
        if not isinstance(self.worktree_ref, str):
            raise ValueError("worktree_ref must be text.")

    def to_dict(self) -> dict[str, Any]:
        return {"recent_actions": list(self.recent_actions), "log_refs": list(self.log_refs), "command_output": list(self.command_output), "memory_refs": list(self.memory_refs), "file_anchors": list(self.file_anchors), "worktree_ref": self.worktree_ref, "schema_version": self.schema_version}


@dataclass(frozen=True, slots=True)
class DiagnosisReport:
    """Placeholder-compatible diagnosis output contract for later steps."""

    category: FailureCategory
    root_cause: str
    confidence: float
    evidence_summary: str
    recommended_strategy: RecoveryStrategy
    schema_version: int = RECOVERY_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {"category": self.category.value, "root_cause": self.root_cause, "confidence": self.confidence, "evidence_summary": self.evidence_summary, "recommended_strategy": self.recommended_strategy.value, "schema_version": self.schema_version}


@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    """Bounded recovery strategy decision contract."""

    strategy: RecoveryStrategy
    reason: str
    context_delta: str = ""
    backoff_seconds: int = 0
    preserve_worktree: bool = True
    max_attempts_after_plan: int = 0
    schema_version: int = RECOVERY_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {"strategy": self.strategy.value, "reason": self.reason, "context_delta": self.context_delta, "backoff_seconds": self.backoff_seconds, "preserve_worktree": self.preserve_worktree, "max_attempts_after_plan": self.max_attempts_after_plan, "schema_version": self.schema_version}


@dataclass(frozen=True, slots=True)
class RecoveryOutcome:
    """Terminal recovery outcome contract."""

    task_id: str
    status: str
    notes: str = ""
    references: tuple[str, ...] = ()
    schema_version: int = RECOVERY_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "status": self.status, "notes": self.notes, "references": list(self.references), "schema_version": self.schema_version}


@dataclass(frozen=True, slots=True)
class RecoveryRecord:
    """Replayable aggregate record for a future recovery ledger."""

    event: FailureEvent
    diagnosis: DiagnosisReport | None = None
    plan: RecoveryPlan | None = None
    outcome: RecoveryOutcome | None = None
    timestamp: str = ""
    schema_version: int = RECOVERY_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {"event": self.event.to_dict(), "diagnosis": self.diagnosis.to_dict() if self.diagnosis else None, "plan": self.plan.to_dict() if self.plan else None, "outcome": self.outcome.to_dict() if self.outcome else None, "timestamp": self.timestamp, "schema_version": self.schema_version}
