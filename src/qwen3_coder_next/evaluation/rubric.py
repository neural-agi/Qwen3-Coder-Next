"""Deterministic task-to-rubric construction."""
from qwen3_coder_next.evaluation.schemas import EvaluationRubric, EvaluationRunRequest, RubricCriterion

class RubricBuilder:
    def build(self, request: EvaluationRunRequest) -> EvaluationRubric:
        if not isinstance(request, EvaluationRunRequest): raise ValueError("request must be an EvaluationRunRequest.")
        return EvaluationRubric((RubricCriterion("semantic-mismatch", "The patch addresses the task specification.", 2.0, True), RubricCriterion("evidence-complete", "Required test and review evidence is present."), RubricCriterion("plan-consistent", "The patch remains consistent with the plan.")), policy_version=request.policy_version)
