"""Evaluation abstraction for the foundation layer."""

from abc import ABC, abstractmethod

from qwen3_coder_next.evaluation.contracts import EvaluationOutcome, EvaluationRequest


class Evaluator(ABC):
    """Abstract evaluator interface."""

    @abstractmethod
    def evaluate(self, request: EvaluationRequest) -> EvaluationOutcome:
        """Evaluate the supplied request."""
