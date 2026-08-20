"""Deterministic test/review gate coordination."""

from __future__ import annotations

from qwen3_coder_next.quality.schemas import FeedbackBundle, GateDecision, ReviewReport, TestReport


class GateCoordinator:
    """Combine independent test and review reports without reinterpreting evidence."""

    def decide(self, test_report: TestReport, review_report: ReviewReport) -> tuple[GateDecision, FeedbackBundle]:
        if not isinstance(test_report, TestReport) or not isinstance(review_report, ReviewReport):
            raise ValueError("test_report and review_report are required.")
        if test_report.task_id != review_report.task_id:
            raise ValueError("reports must refer to the same task.")
        reasons: list[str] = []
        blocking: list[str] = []
        retryable: list[str] = []
        if test_report.status != "pass":
            reasons.append(f"tests:{test_report.status}")
            retryable.extend(test_report.failed_cases or ("test-suite",))
        if review_report.overall_status != "pass":
            reasons.append(f"review:{review_report.overall_status}")
            blocking.extend(finding.id for finding in review_report.findings)
        decision = "pass" if not reasons else "reject"
        next_action = "proceed" if decision == "pass" else "retry" if retryable else "escalate"
        gate = GateDecision(test_report.task_id, decision, tuple(reasons), tuple(blocking), tuple(retryable), next_action)
        feedback = FeedbackBundle(test_report.task_id, "Quality gate passed." if decision == "pass" else "Quality gate rejected the candidate.", tuple(reasons), tuple(retryable))
        return gate, feedback
