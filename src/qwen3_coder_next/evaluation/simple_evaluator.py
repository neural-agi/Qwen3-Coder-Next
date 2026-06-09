"""Deterministic evaluator implementation."""

from qwen3_coder_next.evaluation.contracts import (
    EvaluationOutcome,
    EvaluationRequest,
    EvaluationScore,
    EvaluationStatus,
)
from qwen3_coder_next.evaluation.evaluator import Evaluator


class SimpleEvaluator(Evaluator):
    """Return a deterministic evaluation outcome."""

    def evaluate(self, request: EvaluationRequest) -> EvaluationOutcome:
        """Evaluate by returning a fixed pass outcome for the supplied content."""

        return EvaluationOutcome(
            request_id=request.request_id,
            status=EvaluationStatus.PASSED,
            score=EvaluationScore(value=1.0, label="pass"),
            summary=f"Evaluation complete for: {request.target}",
        )
