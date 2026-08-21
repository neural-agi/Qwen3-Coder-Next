"""Deterministic scenario, chaos, safety, and replay coverage for recovery."""
import unittest

from qwen3_coder_next.recovery import (
    CheckpointManager,
    CheckpointResult,
    CheckpointRollbackAdapter,
    DiagnosisReport,
    EvidenceBundle,
    FailureCategory,
    FailureClassifier,
    FailureEvent,
    InMemoryRecoveryLedger,
    InMemoryRecoveryMetrics,
    RecoveryAttemptResult,
    RecoveryExecutionAdapter,
    RecoveryExecutor,
    RecoveryPlan,
    RecoveryStrategy,
    Severity,
    StrategyRegistry,
)


class ScenarioAdapter(RecoveryExecutionAdapter):
    def __init__(self, results):
        self.results = tuple(results)
        self.calls = []

    def execute(self, plan, *, attempt):
        self.calls.append((plan.strategy.value, attempt))
        return self.results[attempt - 1] if attempt <= len(self.results) else RecoveryAttemptResult(False, "adapter exhausted")


class CheckpointAdapter(CheckpointRollbackAdapter):
    def __init__(self, rollback_success=True):
        self.rollback_success = rollback_success
        self.calls = []

    def create_checkpoint(self, event, evidence):
        self.calls.append(("create", event.worktree_ref))
        return "checkpoint-not-used"  # The scenario verifies the manager rejects this.

    def rollback(self, checkpoint):
        self.calls.append(("rollback", checkpoint))
        return CheckpointResult(self.rollback_success, "rollback", "restored" if self.rollback_success else "failed")


class RecoveryStep9SmokeTest(unittest.TestCase):
    def _event(self, failure_type, message, source="coding", retry_count=0):
        return FailureEvent("task-step9", source, failure_type, Severity.HIGH, message, "epoch", retry_count=retry_count, worktree_ref="isolated-wt")

    def _run(self, event, output, adapter, ledger, metrics):
        evidence = EvidenceBundle(command_output=(output,), worktree_ref=event.worktree_ref, log_refs=("logs/failure",))
        diagnosis = FailureClassifier().classify(event, evidence)
        plan = StrategyRegistry().select(diagnosis, event)
        outcome = RecoveryExecutor().execute(event, evidence, diagnosis, plan, adapter, ledger=ledger, metrics=metrics)
        return evidence, diagnosis, plan, outcome

    def test_failure_corpus_covers_every_defined_category_and_terminal_record(self):
        cases = (
            (FailureCategory.TRANSIENT, "timeout", "timeout", ScenarioAdapter((RecoveryAttemptResult(True, "resumed"),))),
            (FailureCategory.SEMANTIC, "assertion", "assertion failed", ScenarioAdapter((RecoveryAttemptResult(True, "alternative"),))),
            (FailureCategory.ENVIRONMENTAL, "permission", "permission denied", ScenarioAdapter((RecoveryAttemptResult(True, "fixed"),))),
            (FailureCategory.UNRECOVERABLE, "corrupt", "corrupt state", None),
            (FailureCategory.UNKNOWN, "unknown", "unrecognized condition", None),
        )
        ledger = InMemoryRecoveryLedger()
        metrics = InMemoryRecoveryMetrics()
        for expected, failure_type, message, adapter in cases:
            evidence, diagnosis, plan, outcome = self._run(self._event(failure_type, message), message, adapter, ledger, metrics)
            self.assertEqual(diagnosis.category, expected)
            self.assertTrue(outcome.status in {"resumed", "aborted", "escalated"})
            self.assertEqual(ledger.records[-1].event.task_id, "task-step9")
            self.assertEqual(ledger.records[-1].event.worktree_ref, evidence.worktree_ref)
            self.assertIs(ledger.records[-1].diagnosis, diagnosis)
            self.assertIs(ledger.records[-1].plan, plan)
        self.assertEqual(len(ledger.records), len(cases))

    def test_deterministic_chaos_matrix_and_bounded_retry(self):
        chaos_cases = ("timeout", "permission denied", "tool crash", "malformed output", "out of memory")
        for message in chaos_cases:
            event = self._event("timeout" if message == "timeout" else message.replace(" ", "_"), message)
            adapter = ScenarioAdapter((RecoveryAttemptResult(False, "failed"), RecoveryAttemptResult(False, "failed again")))
            ledger = InMemoryRecoveryLedger()
            metrics = InMemoryRecoveryMetrics()
            _, diagnosis, plan, outcome = self._run(event, message, adapter, ledger, metrics)
            self.assertLessEqual(len(adapter.calls), plan.max_attempts_after_plan)
            self.assertEqual(len(ledger.records), 1)
            self.assertIn(outcome.status, {"retryable_failure", "escalated", "aborted"})

    def test_replay_produces_identical_diagnosis_strategy_and_outcome(self):
        event = self._event("timeout", "timeout")
        first = self._run(event, "timeout", ScenarioAdapter((RecoveryAttemptResult(False, "failed"), RecoveryAttemptResult(True, "ok"))), InMemoryRecoveryLedger(), InMemoryRecoveryMetrics())
        second = self._run(event, "timeout", ScenarioAdapter((RecoveryAttemptResult(False, "failed"), RecoveryAttemptResult(True, "ok"))), InMemoryRecoveryLedger(), InMemoryRecoveryMetrics())
        self.assertEqual(first[1].to_dict(), second[1].to_dict())
        self.assertEqual(first[2].to_dict(), second[2].to_dict())
        self.assertEqual(first[3].to_dict(), second[3].to_dict())

    def test_safe_abort_preserves_evidence_and_worktree_reference(self):
        event = self._event("corrupt", "corrupt state", source="review")
        ledger = InMemoryRecoveryLedger()
        evidence, diagnosis, plan, outcome = self._run(event, "corrupt state", None, ledger, InMemoryRecoveryMetrics())
        self.assertEqual(outcome.status, "aborted")
        record = ledger.records[0]
        self.assertEqual(record.event.worktree_ref, "isolated-wt")
        self.assertEqual(record.event.raw_payload, "")
        self.assertEqual(record.outcome.status, "aborted")
        self.assertEqual(evidence.worktree_ref, "isolated-wt")
        self.assertEqual(diagnosis.category, FailureCategory.UNRECOVERABLE)
        self.assertEqual(plan.strategy, RecoveryStrategy.ABORT)

    def test_checkpoint_failure_is_explicit_and_does_not_mutate_recovery_contracts(self):
        event = self._event("timeout", "timeout")
        evidence = EvidenceBundle(worktree_ref="isolated-wt")
        adapter = CheckpointAdapter()
        manager = CheckpointManager(adapter)
        with self.assertRaises(ValueError):
            manager.create(event, evidence)
        self.assertEqual(event.retry_count, 0)
        self.assertEqual(adapter.calls, [("create", "isolated-wt")])

    def test_ledger_and_metrics_failures_are_not_silently_converted(self):
        class BrokenLedger(InMemoryRecoveryLedger):
            def append(self, record):
                raise RuntimeError("ledger unavailable")

        event = self._event("timeout", "timeout")
        with self.assertRaises(RuntimeError):
            self._run(event, "timeout", ScenarioAdapter((RecoveryAttemptResult(True, "ok"),)), BrokenLedger(), InMemoryRecoveryMetrics())


if __name__ == "__main__":
    unittest.main()
