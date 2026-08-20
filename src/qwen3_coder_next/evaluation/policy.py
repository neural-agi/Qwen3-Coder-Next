"""Hard decision policy for evaluation outcomes."""
from qwen3_coder_next.evaluation.schemas import EvaluationDecision, EvaluationRubric, EvaluationRunRequest, CriterionScore, EvidenceBundle

class DecisionPolicy:
    def decide(self, request: EvaluationRunRequest, rubric: EvaluationRubric, scores: tuple[CriterionScore, ...], evidence: EvidenceBundle) -> EvaluationDecision:
        if evidence.missing_items: return EvaluationDecision(request.task_id, "escalate", 0.0, (), evidence.missing_items, "Critical evidence is missing.", "request_additional_evidence", rubric.policy_version)
        total = sum(c.weight for c in rubric.criteria); aggregate = sum(c.weight * next(s.score for s in scores if s.criterion_id == c.criterion_id) for c in rubric.criteria) / total
        blockers = tuple(c.criterion_id for c in rubric.criteria if c.hard_fail and next(s.score for s in scores if s.criterion_id == c.criterion_id) < 1.0)
        decision = "reject" if blockers or aggregate < rubric.approval_threshold else "approve"
        return EvaluationDecision(request.task_id, decision, aggregate, blockers, (), "Rubric and evidence evaluated deterministically.", "return_to_coding_with_feedback" if decision == "reject" else "proceed", rubric.policy_version)
