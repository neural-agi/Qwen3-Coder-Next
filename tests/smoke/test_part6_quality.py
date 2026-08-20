"""Part 6 quality gate acceptance coverage."""

import sys
import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from qwen3_coder_next.quality import (
    GateCoordinator, QualityArtifactPublisher, QualityReportSerializer, ResultNormalizer, ReviewInstruction,
    ReviewOrchestrator, TestInvocation, TestOrchestrator,
)


class Part6QualitySmokeTest(unittest.TestCase):
    def test_passing_command_review_gate_and_artifact_round_trip(self) -> None:
        with TemporaryDirectory() as directory:
            invocation = TestInvocation("quality-1", "worktree-1", "python", (sys.executable, "-c", "print('ok')"), 10, directory, "test")
            raw = TestOrchestrator().run(invocation)
            report = ResultNormalizer().normalize(invocation, raw, suite_name="fixture-pass")
            self.assertEqual(QualityReportSerializer().deserialize_test_report(QualityReportSerializer().serialize(report)), report)
            review = ReviewOrchestrator().review(ReviewInstruction("quality-1", "diff://fixture", "default", 1000, "strict"), "", worktree_id="worktree-1")
            decision, feedback = GateCoordinator().decide(report, review)
            self.assertEqual(decision.decision, "pass")
            self.assertEqual(feedback.rerun_hints, ())
            path = QualityArtifactPublisher(Path(directory) / "artifacts").publish("quality-1", "report", report.to_dict())
            self.assertTrue((Path(directory) / "artifacts" / path).exists())

    def test_failure_timeout_and_review_rejection_are_distinct(self) -> None:
        with TemporaryDirectory() as directory:
            invocation = TestInvocation("quality-2", "worktree-2", "python", (sys.executable, "-c", "raise SystemExit(1)"), 10, directory, "test")
            report = ResultNormalizer().normalize(invocation, TestOrchestrator().run(invocation), suite_name="fixture-fail")
            self.assertEqual(report.status, "fail")
            review = ReviewOrchestrator().review(ReviewInstruction("quality-2", "diff://fixture", "default", 1000, "strict"), "<<<<<<< conflict", worktree_id="worktree-2")
            decision, _ = GateCoordinator().decide(report, review)
            self.assertEqual(decision.decision, "reject")
            self.assertIn("tests:fail", decision.reasons)
            self.assertIn("review:reject", decision.reasons)

    def test_timeout_is_normalized_and_report_shape_matches_golden(self) -> None:
        with TemporaryDirectory() as directory:
            invocation = TestInvocation("quality-timeout", "worktree-timeout", "python", (sys.executable, "-c", "import time; time.sleep(2)"), 1, directory, "test")
            report = ResultNormalizer().normalize(invocation, TestOrchestrator().run(invocation), suite_name="fixture-timeout")
            self.assertEqual(report.status, "timeout")
            golden_invocation = TestInvocation("quality-golden", "worktree-golden", "python", (sys.executable, "-c", "print('ok')"), 10, directory, "test")
            golden = ResultNormalizer().normalize(golden_invocation, TestOrchestrator().run(golden_invocation), suite_name="fixture-pass")
            fixture = Path(__file__).parents[1] / "fixtures" / "part6_pass_report.json"
            self.assertEqual(golden.to_dict(), json.loads(fixture.read_text(encoding="utf-8")))

    def test_contracts_reject_malformed_inputs(self) -> None:
        with self.assertRaises(ValueError):
            TestInvocation("task", "worktree", "python", (), 0, ".", "test")
        with self.assertRaises(ValueError):
            ReviewOrchestrator().review("bad", "", worktree_id="w")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
