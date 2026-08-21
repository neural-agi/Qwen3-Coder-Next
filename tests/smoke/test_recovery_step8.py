import unittest

from qwen3_coder_next.recovery import (
    DiagnosisReport,
    EvidenceBundle,
    FailureCategory,
    FailureEvent,
    InMemoryRecoveryLedger,
    InMemoryRecoveryMetrics,
    RecoveryAttemptResult,
    RecoveryExecutionAdapter,
    RecoveryExecutor,
    RecoveryPlan,
    RecoveryStrategy,
    Severity,
)


class Adapter(RecoveryExecutionAdapter):
    def execute(self, plan, *, attempt):
        return RecoveryAttemptResult(True, "completed", (f"attempt-{attempt}",))


class RecoveryStep8SmokeTest(unittest.TestCase):
    def setUp(self):
        self.event = FailureEvent("task-8", "testing", "timeout", Severity.HIGH, "timeout", "epoch")
        self.evidence = EvidenceBundle(command_output=("timeout",))
        self.diagnosis = DiagnosisReport(FailureCategory.TRANSIENT, "timeout", 0.8, "evidence_items=1")
        self.plan = RecoveryPlan(RecoveryStrategy.RETRY_SAME, "retry", max_attempts_after_plan=1)

    def test_terminal_outcome_is_persisted_and_metrics_emitted(self):
        ledger = InMemoryRecoveryLedger()
        metrics = InMemoryRecoveryMetrics()
        outcome = RecoveryExecutor().execute(
            self.event, self.evidence, self.diagnosis, self.plan, Adapter(), ledger=ledger, metrics=metrics, elapsed_seconds=0.25
        )
        self.assertEqual(outcome.status, "resumed")
        self.assertEqual(len(ledger.records), 1)
        self.assertEqual(ledger.records[0].outcome, outcome)
        self.assertEqual(metrics.outcome_counts, {"resumed": 1})
        self.assertEqual(metrics.retry_count, 1)
        self.assertEqual(metrics.elapsed_seconds, 0.25)

    def test_escalation_records_without_execution(self):
        ledger = InMemoryRecoveryLedger()
        metrics = InMemoryRecoveryMetrics()
        outcome = RecoveryExecutor().execute(
            self.event, self.evidence, self.diagnosis,
            RecoveryPlan(RecoveryStrategy.ESCALATE, "unsafe"),
            ledger=ledger, metrics=metrics,
        )
        self.assertEqual(outcome.status, "escalated")
        self.assertEqual(metrics.escalation_count, 1)
        self.assertEqual(ledger.records[0].event, self.event)

    def test_invalid_writer_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            RecoveryExecutor().execute(self.event, self.evidence, self.diagnosis, self.plan, Adapter(), ledger=object())
        with self.assertRaises(ValueError):
            RecoveryExecutor().execute(self.event, self.evidence, self.diagnosis, self.plan, Adapter(), elapsed_seconds=-1)

    def test_ledger_order_and_record_serialization_are_deterministic(self):
        ledger = InMemoryRecoveryLedger()
        executor = RecoveryExecutor()
        executor.execute(self.event, self.evidence, self.diagnosis, self.plan, Adapter(), ledger=ledger)
        executor.execute(self.event, self.evidence, self.diagnosis, self.plan, Adapter(), ledger=ledger)
        self.assertEqual(len(ledger.records), 2)
        self.assertEqual(ledger.records[0].to_dict(), ledger.records[1].to_dict())


if __name__ == "__main__":
    unittest.main()
