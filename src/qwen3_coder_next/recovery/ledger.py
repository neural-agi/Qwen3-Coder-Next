"""Injected recovery ledger boundary and deterministic in-process implementation."""
from __future__ import annotations

from abc import ABC, abstractmethod

from qwen3_coder_next.recovery.contracts import RecoveryRecord


class RecoveryLedger(ABC):
    """Caller-owned boundary for durable recovery-record persistence."""

    @abstractmethod
    def append(self, record: RecoveryRecord) -> None:
        """Persist one terminal recovery record."""


class InMemoryRecoveryLedger(RecoveryLedger):
    """Append-only ledger useful for deterministic runtime and test integration."""

    def __init__(self) -> None:
        self._records: tuple[RecoveryRecord, ...] = ()

    def append(self, record: RecoveryRecord) -> None:
        if not isinstance(record, RecoveryRecord):
            raise ValueError("record must be a RecoveryRecord.")
        self._records = self._records + (record,)

    @property
    def records(self) -> tuple[RecoveryRecord, ...]:
        """Return the immutable append-only record snapshot."""
        return self._records


class RecoveryMetrics(ABC):
    """Injected boundary for recovery counters and timers."""

    @abstractmethod
    def record(self, record: RecoveryRecord, *, attempts: int, elapsed_seconds: float) -> None:
        """Emit metrics for one terminal recovery decision."""


class InMemoryRecoveryMetrics(RecoveryMetrics):
    """Deterministic counter/timer accumulator for local integration and tests."""

    def __init__(self) -> None:
        self.retry_count = 0
        self.outcome_counts: dict[str, int] = {}
        self.escalation_count = 0
        self.elapsed_seconds = 0.0

    def record(self, record: RecoveryRecord, *, attempts: int, elapsed_seconds: float) -> None:
        if not isinstance(record, RecoveryRecord) or not isinstance(attempts, int) or attempts < 0:
            raise ValueError("invalid recovery metric input.")
        if not isinstance(elapsed_seconds, (int, float)) or elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must be non-negative.")
        status = record.outcome.status if record.outcome else "unknown"
        self.retry_count += attempts
        self.outcome_counts[status] = self.outcome_counts.get(status, 0) + 1
        if status == "escalated":
            self.escalation_count += 1
        self.elapsed_seconds += float(elapsed_seconds)
