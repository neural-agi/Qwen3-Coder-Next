import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from qwen3_coder_next.evaluation import BenchmarkCase, EvaluationAuditStore, EvaluationCoordinator, EvaluationRunRequest, run_benchmark

class EvaluationPart7SmokeTest(unittest.TestCase):
    def _request(self, **kwargs):
        values = {"task_id": "eval-7", "task_spec": "implement cache", "plan_summary": "cache plan", "patch_summary": "cache implementation", "test_artifacts": ("tests-pass",), "review_notes": ("review-pass",)}
        values.update(kwargs)
        return EvaluationRunRequest(**values)
    def test_approve_reject_escalate_and_deterministic_audit(self):
        with TemporaryDirectory() as d:
            audit = EvaluationAuditStore(Path(d) / "audit.json"); coordinator = EvaluationCoordinator(audit)
            approve, _ = coordinator.evaluate(self._request(), timestamp="epoch")
            self.assertEqual(approve.decision, "approve")
            reject, feedback = coordinator.evaluate(self._request(patch_summary="wrong implementation"), timestamp="epoch")
            self.assertEqual(reject.decision, "reject")
            self.assertEqual(feedback.rejected_criteria, ("semantic-mismatch",))
            escalate, _ = coordinator.evaluate(self._request(test_artifacts=()), timestamp="epoch")
            self.assertEqual(escalate.decision, "escalate")
            self.assertEqual(len(audit.records()), 3)
            self.assertEqual(audit.records()[0]["policy_version"], "default")

    def test_missing_evidence_never_approves_and_replay_is_stable(self):
        request = self._request(review_notes=())
        first = EvaluationCoordinator().evaluate(request); second = EvaluationCoordinator().evaluate(request)
        self.assertEqual(first, second); self.assertEqual(first[0].decision, "escalate")
    def test_malformed_request_rejected(self):
        with self.assertRaises(ValueError): EvaluationCoordinator().evaluate("bad")

    def test_golden_cases_and_benchmark_metrics(self):
        cases = (
            BenchmarkCase(self._request(), "approve", 1.0),
            BenchmarkCase(self._request(patch_summary="wrong implementation"), "reject", 1.0),
            BenchmarkCase(self._request(test_artifacts=()), "escalate", 1.0),
        )
        result = run_benchmark(cases)
        self.assertEqual(result.case_count, 3)
        self.assertAlmostEqual(result.approval_rate, 1 / 3)
        self.assertEqual(result.false_approval_rate, 0.0)
        self.assertEqual(result.average_latency_ms, 1.0)

if __name__ == "__main__": unittest.main()
