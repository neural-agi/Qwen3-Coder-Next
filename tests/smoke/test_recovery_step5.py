import unittest

from qwen3_coder_next.recovery import (
    DiagnosisReport,
    FailureCategory,
    FailureEvent,
    RecoveryStrategy,
    Severity,
    StrategyRegistry,
)


class RecoveryStep5SmokeTest(unittest.TestCase):
    def _event(self, retry_count=0):
        return FailureEvent("task-5", "testing", "timeout", Severity.HIGH, "timeout", "epoch", retry_count=retry_count)

    def _diagnosis(self, category):
        return DiagnosisReport(category, "candidate", 0.8, "evidence_items=1")

    def test_category_strategy_and_budget_mapping(self):
        registry = StrategyRegistry()
        expected = {
            FailureCategory.TRANSIENT: RecoveryStrategy.RETRY_WITH_CONTEXT,
            FailureCategory.SEMANTIC: RecoveryStrategy.ALTERNATIVE_APPROACH,
            FailureCategory.ENVIRONMENTAL: RecoveryStrategy.RETRY_WITH_CONTEXT,
            FailureCategory.UNRECOVERABLE: RecoveryStrategy.ABORT,
            FailureCategory.UNKNOWN: RecoveryStrategy.ESCALATE,
        }
        for category, strategy in expected.items():
            plan = registry.select(self._diagnosis(category), self._event())
            self.assertEqual(plan.strategy, strategy)
            self.assertGreaterEqual(plan.max_attempts_after_plan, 0)

    def test_retry_budget_is_bounded_and_exhaustion_escalates(self):
        registry = StrategyRegistry()
        first = registry.select(self._diagnosis(FailureCategory.TRANSIENT), self._event())
        exhausted = registry.select(self._diagnosis(FailureCategory.TRANSIENT), self._event(retry_count=2))
        self.assertEqual(first.strategy, RecoveryStrategy.RETRY_WITH_CONTEXT)
        self.assertEqual(first.max_attempts_after_plan, 2)
        self.assertEqual(exhausted.strategy, RecoveryStrategy.ESCALATE)
        self.assertEqual(exhausted.max_attempts_after_plan, 0)

    def test_selection_is_deterministic_serializable_and_side_effect_free(self):
        registry = StrategyRegistry()
        diagnosis = self._diagnosis(FailureCategory.SEMANTIC)
        event = self._event()
        first = registry.select(diagnosis, event)
        second = registry.select(diagnosis, event)
        self.assertEqual(first, second)
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(event.retry_count, 0)

    def test_malformed_and_unsupported_inputs_are_rejected(self):
        registry = StrategyRegistry()
        with self.assertRaises(ValueError):
            registry.select("bad", self._event())
        with self.assertRaises(ValueError):
            StrategyRegistry({"bad": "rule"})


if __name__ == "__main__":
    unittest.main()
