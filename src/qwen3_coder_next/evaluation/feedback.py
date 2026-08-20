"""Structured evaluation feedback."""
from qwen3_coder_next.evaluation.schemas import EvaluationDecision, FeedbackPacket

class FeedbackGenerator:
    def generate(self, decision: EvaluationDecision) -> FeedbackPacket:
        if not isinstance(decision, EvaluationDecision): raise ValueError("decision is required.")
        return FeedbackPacket(decision.task_id, decision.blockers, decision.warnings, tuple(f"Address {item}." for item in decision.blockers), "Additional evidence required." if decision.decision == "escalate" else "")

