"""Smoke tests for the evaluation foundation."""

import unittest

from qwen3_coder_next.evaluation import (
    EvaluationOutcome,
    EvaluationRequest,
    EvaluationResult,
    EvaluationScore,
    EvaluationStatus,
    Evaluator,
    SimpleEvaluator,
)


class EvaluationFoundationSmokeTest(unittest.TestCase):
    """Verify evaluation contracts, abstraction, and deterministic implementation."""

    def test_evaluation_contracts_can_be_created(self) -> None:
        """Create each evaluation contract type."""

        score = EvaluationScore(value=0.75, label="partial")
        request = EvaluationRequest(
            request_id="eval-001",
            target="tool-output",
            content="hello",
        )
        outcome = EvaluationOutcome(
            request_id="eval-001",
            status=EvaluationStatus.PASSED,
            score=score,
            summary="Looks good",
        )
        result = EvaluationResult(outcome=outcome)

        self.assertEqual(score.value, 0.75)
        self.assertEqual(request.target, "tool-output")
        self.assertEqual(outcome.status, EvaluationStatus.PASSED)
        self.assertEqual(result.outcome, outcome)

    def test_simple_evaluator_returns_deterministic_outcome(self) -> None:
        """Return a fixed pass outcome for a request."""

        evaluator = SimpleEvaluator()
        outcome = evaluator.evaluate(
            EvaluationRequest(
                request_id="eval-002",
                target="prompt-output",
                content="sample",
            )
        )

        self.assertIsInstance(evaluator, Evaluator)
        self.assertEqual(outcome.status, EvaluationStatus.PASSED)
        self.assertEqual(outcome.score.value, 1.0)
        self.assertEqual(outcome.summary, "Evaluation complete for: prompt-output")
