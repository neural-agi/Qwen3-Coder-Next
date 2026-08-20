"""Standalone evaluation coordinator."""
from qwen3_coder_next.evaluation.audit import EvaluationAuditStore
from qwen3_coder_next.evaluation.evidence import EvidenceCollector
from qwen3_coder_next.evaluation.feedback import FeedbackGenerator
from qwen3_coder_next.evaluation.policy import DecisionPolicy
from qwen3_coder_next.evaluation.rubric import RubricBuilder
from qwen3_coder_next.evaluation.scoring import ScoreEngine
from qwen3_coder_next.evaluation.schemas import EvaluationDecision, EvaluationRunRequest, FeedbackPacket

class EvaluationCoordinator:
    def __init__(self, audit_store: EvaluationAuditStore | None = None) -> None: self._audit = audit_store
    def evaluate(self, request: EvaluationRunRequest, *, timestamp: str = "epoch") -> tuple[EvaluationDecision, FeedbackPacket]:
        evidence = EvidenceCollector().collect(request); rubric = RubricBuilder().build(request); scores = ScoreEngine().score(rubric, evidence, request); decision = DecisionPolicy().decide(request, rubric, scores, evidence); feedback = FeedbackGenerator().generate(decision)
        if self._audit is not None: self._audit.append(decision, timestamp=timestamp)
        return decision, feedback

