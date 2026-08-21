import unittest

from qwen3_coder_next.recovery import (
    DiagnosisReport,
    EvidenceBundle,
    FailureCategory,
    FailureEvent,
    RecoveryAttemptResult,
    RecoveryExecutionAdapter,
    RecoveryExecutor,
    RecoveryPlan,
    RecoveryStrategy,
    Severity,
    StrategyRegistry,
)


class Adapter(RecoveryExecutionAdapter):
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def execute(self, plan, *, attempt):
        self.calls.append(attempt)
        return self.results[attempt - 1]


class RecoveryStep6SmokeTest(unittest.TestCase):
    def setUp(self):
        self.event = FailureEvent("task-6", "testing", "timeout", Severity.HIGH, "timeout", "epoch")
        self.evidence = EvidenceBundle(command_output=("timeout",))
        self.diagnosis = DiagnosisReport(FailureCategory.TRANSIENT, "timeout", 0.8, "evidence_items=1")

    def test_success_and_bounded_retry_execution(self):
        plan = StrategyRegistry().select(self.diagnosis, self.event)
        adapter = Adapter((RecoveryAttemptResult(False, "first failed"), RecoveryAttemptResult(True, "resumed", ("attempt-2",))))
        outcome = RecoveryExecutor().execute(self.event, self.evidence, self.diagnosis, plan, adapter)
        self.assertEqual(outcome.status, "resumed")
        self.assertEqual(adapter.calls, [1, 2])
        self.assertEqual(outcome.to_dict()["references"], ["attempt-2"])

    def test_retryable_failure_and_exhausted_budget(self):
        plan = RecoveryPlan(RecoveryStrategy.RETRY_WITH_CONTEXT, "retry", max_attempts_after_plan=2)
        adapter = Adapter((RecoveryAttemptResult(False, "failed"), RecoveryAttemptResult(False, "failed again")))
        outcome = RecoveryExecutor().execute(self.event, self.evidence, self.diagnosis, plan, adapter)
        self.assertEqual(outcome.status, "retryable_failure")
        exhausted = RecoveryPlan(RecoveryStrategy.RETRY_WITH_CONTEXT, "none", max_attempts_after_plan=0)
        self.assertEqual(RecoveryExecutor().execute(self.event, self.evidence, self.diagnosis, exhausted, adapter).status, "exhausted")

    def test_escalation_and_abort_do_not_execute_adapter(self):
        adapter = Adapter(())
        for strategy, expected in ((RecoveryStrategy.ESCALATE, "escalated"), (RecoveryStrategy.ABORT, "aborted")):
            plan = RecoveryPlan(strategy, "terminal")
            outcome = RecoveryExecutor().execute(self.event, self.evidence, self.diagnosis, plan, adapter)
            self.assertEqual(outcome.status, expected)
        self.assertEqual(adapter.calls, [])

    def test_malformed_adapter_and_inputs_are_rejected(self):
        executor = RecoveryExecutor()
        plan = RecoveryPlan(RecoveryStrategy.RETRY_SAME, "retry", max_attempts_after_plan=1)
        with self.assertRaises(ValueError):
            executor.execute("bad", self.evidence, self.diagnosis, plan)
        with self.assertRaises(ValueError):
            executor.execute(self.event, self.evidence, self.diagnosis, plan)
        with self.assertRaises(ValueError):
            executor.execute(self.event, self.evidence, self.diagnosis, plan, object())

    def test_attempt_result_is_immutable_and_no_rollback_is_present(self):
        result = RecoveryAttemptResult(True, "ok")
        with self.assertRaises(AttributeError):
            result.success = False
        self.assertFalse(hasattr(RecoveryExecutor, "rollback"))


if __name__ == "__main__":
    unittest.main()
