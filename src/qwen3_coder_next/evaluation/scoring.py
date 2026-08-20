"""Pure deterministic rubric scoring."""
from qwen3_coder_next.evaluation.schemas import CriterionScore, EvaluationRubric, EvidenceBundle, EvaluationRunRequest

class ScoreEngine:
    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {token for token in value.lower().replace("-", " ").split() if len(token) > 2}

    def score(self, rubric: EvaluationRubric, evidence: EvidenceBundle, request: EvaluationRunRequest) -> tuple[CriterionScore, ...]:
        if not isinstance(rubric, EvaluationRubric) or not isinstance(evidence, EvidenceBundle): raise ValueError("rubric and evidence are required.")
        task_tokens = self._tokens(request.task_spec)
        aligned = bool(task_tokens) and bool(task_tokens.intersection(self._tokens(evidence.normalized_diff)))
        complete = not evidence.missing_items
        values = {"semantic-mismatch": (1.0 if aligned else 0.0, "patch addresses task terms" if aligned else "patch does not match task terms"), "evidence-complete": (1.0 if complete else 0.0, "required evidence present" if complete else "required evidence missing"), "plan-consistent": (1.0 if request.plan_summary.strip() and aligned else 0.0, "plan and patch are present" if request.plan_summary.strip() and aligned else "plan or patch evidence missing")}
        return tuple(CriterionScore(c.criterion_id, values[c.criterion_id][0], 1.0, values[c.criterion_id][1]) for c in rubric.criteria)
