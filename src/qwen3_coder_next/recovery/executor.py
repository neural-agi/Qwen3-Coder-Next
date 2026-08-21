"""Bounded execution of an already-selected recovery plan."""
from __future__ import annotations

from abc import ABC, abstractmethod

from qwen3_coder_next.recovery.contracts import (
    DiagnosisReport,
    EvidenceBundle,
    FailureEvent,
    RecoveryOutcome,
    RecoveryPlan,
    RecoveryRecord,
    RecoveryStrategy,
)
from qwen3_coder_next.recovery.ledger import RecoveryLedger, RecoveryMetrics


class RecoveryExecutionAdapter(ABC):
    """Injected boundary for one safe recovery attempt."""

    @abstractmethod
    def execute(self, plan: RecoveryPlan, *, attempt: int) -> "RecoveryAttemptResult":
        """Execute one already-approved attempt in the caller's safety boundary."""


class RecoveryAttemptResult:
    """Immutable result returned by a recovery execution adapter."""

    __slots__ = ("success", "notes", "references")

    def __init__(self, success: bool, notes: str = "", references: tuple[str, ...] = ()) -> None:
        if not isinstance(success, bool) or not isinstance(notes, str):
            raise ValueError("invalid recovery attempt result.")
        if isinstance(references, (str, bytes)) or any(not isinstance(item, str) for item in references):
            raise ValueError("references must be text values.")
        object.__setattr__(self, "success", success)
        object.__setattr__(self, "notes", notes)
        object.__setattr__(self, "references", tuple(references))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("RecoveryAttemptResult is immutable.")


class RecoveryExecutor:
    """Execute one bounded recovery plan without selecting or persisting it."""

    def execute(
        self,
        event: FailureEvent,
        evidence: EvidenceBundle,
        diagnosis: DiagnosisReport,
        plan: RecoveryPlan,
        adapter: RecoveryExecutionAdapter | None = None,
        *,
        ledger: RecoveryLedger | None = None,
        metrics: RecoveryMetrics | None = None,
        elapsed_seconds: float = 0.0,
    ) -> RecoveryOutcome:
        if not all(isinstance(value, expected) for value, expected in ((event, FailureEvent), (evidence, EvidenceBundle), (diagnosis, DiagnosisReport), (plan, RecoveryPlan))):
            raise ValueError("event, evidence, diagnosis, and plan are required.")
        if ledger is not None and not isinstance(ledger, RecoveryLedger):
            raise ValueError("ledger must implement RecoveryLedger.")
        if metrics is not None and not isinstance(metrics, RecoveryMetrics):
            raise ValueError("metrics must implement RecoveryMetrics.")
        if not isinstance(elapsed_seconds, (int, float)) or elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must be non-negative.")

        def finalize(outcome: RecoveryOutcome, attempts: int = 0) -> RecoveryOutcome:
            record = RecoveryRecord(event, diagnosis, plan, outcome, event.timestamp)
            if ledger is not None:
                ledger.append(record)
            if metrics is not None:
                metrics.record(record, attempts=attempts, elapsed_seconds=float(elapsed_seconds))
            return outcome

        if plan.strategy in (RecoveryStrategy.ESCALATE, RecoveryStrategy.ABORT):
            status = "escalated" if plan.strategy is RecoveryStrategy.ESCALATE else "aborted"
            return finalize(RecoveryOutcome(event.task_id, status, plan.reason, ()))
        if adapter is None:
            raise ValueError("an execution adapter is required for executable strategies.")
        if not isinstance(adapter, RecoveryExecutionAdapter):
            raise ValueError("adapter must implement RecoveryExecutionAdapter.")
        attempts = plan.max_attempts_after_plan
        if attempts <= 0:
            return finalize(RecoveryOutcome(event.task_id, "exhausted", "recovery budget is exhausted", ()))
        last = RecoveryAttemptResult(False, "no attempt executed")
        for attempt in range(1, attempts + 1):
            result = adapter.execute(plan, attempt=attempt)
            if not isinstance(result, RecoveryAttemptResult):
                raise ValueError("adapter returned an invalid attempt result.")
            last = result
            if result.success:
                return finalize(RecoveryOutcome(event.task_id, "resumed", result.notes, result.references), attempt)
        return finalize(RecoveryOutcome(event.task_id, "retryable_failure" if attempts > 0 else "exhausted", last.notes, last.references), attempts)
