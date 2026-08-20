"""Versioned contracts for the standalone evaluation decision path."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

EVALUATION_SCHEMA_VERSION = 1

def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip(): raise ValueError(f"{name} must be non-empty.")
    return value

def _texts(value: object, name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)): raise ValueError(f"{name} must be a collection.")
    result = tuple(value or ())  # type: ignore[arg-type]
    if any(not isinstance(item, str) or not item.strip() for item in result): raise ValueError(f"{name} contains invalid text.")
    return result

@dataclass(frozen=True, slots=True)
class EvaluationRunRequest:
    task_id: str; task_spec: str; plan_summary: str; patch_summary: str
    test_artifacts: tuple[str, ...] = (); review_notes: tuple[str, ...] = ()
    memory_refs: tuple[str, ...] = (); policy_version: str = "default"
    schema_version: int = EVALUATION_SCHEMA_VERSION
    def __post_init__(self) -> None:
        for name in ("task_id", "task_spec", "plan_summary", "patch_summary", "policy_version"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in ("test_artifacts", "review_notes", "memory_refs"):
            object.__setattr__(self, name, _texts(getattr(self, name), name))
    def to_dict(self) -> dict[str, Any]:
        return {"task_id":self.task_id,"task_spec":self.task_spec,"plan_summary":self.plan_summary,"patch_summary":self.patch_summary,"test_artifacts":list(self.test_artifacts),"review_notes":list(self.review_notes),"memory_refs":list(self.memory_refs),"policy_version":self.policy_version,"schema_version":self.schema_version}

@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    normalized_tests: tuple[str, ...] = (); normalized_review: tuple[str, ...] = ()
    normalized_diff: str = ""; relevant_memory: tuple[str, ...] = (); missing_items: tuple[str, ...] = ()
    def to_dict(self) -> dict[str, Any]:
        return {"normalized_tests":list(self.normalized_tests),"normalized_review":list(self.normalized_review),"normalized_diff":self.normalized_diff,"relevant_memory":list(self.relevant_memory),"missing_items":list(self.missing_items)}

@dataclass(frozen=True, slots=True)
class RubricCriterion:
    criterion_id: str; description: str; weight: float = 1.0; hard_fail: bool = False
    def __post_init__(self) -> None:
        object.__setattr__(self, "criterion_id", _text(self.criterion_id, "criterion_id")); object.__setattr__(self, "description", _text(self.description, "description"))
        if self.weight <= 0: raise ValueError("weight must be positive.")

@dataclass(frozen=True, slots=True)
class EvaluationRubric:
    criteria: tuple[RubricCriterion, ...]; approval_threshold: float = .75; escalation_threshold: float = .5
    policy_version: str = "default"

    def to_dict(self) -> dict[str, Any]:
        return {"criteria": [criterion.to_dict() for criterion in self.criteria], "approval_threshold": self.approval_threshold, "escalation_threshold": self.escalation_threshold, "policy_version": self.policy_version}

@dataclass(frozen=True, slots=True)
class CriterionScore:
    criterion_id: str; score: float; confidence: float; rationale: str; evidence_refs: tuple[str, ...] = ()
    def __post_init__(self) -> None:
        if not 0 <= self.score <= 1 or not 0 <= self.confidence <= 1: raise ValueError("scores must be between 0 and 1.")

    def to_dict(self) -> dict[str, Any]:
        return {"criterion_id": self.criterion_id, "score": self.score, "confidence": self.confidence, "rationale": self.rationale, "evidence_refs": list(self.evidence_refs)}

@dataclass(frozen=True, slots=True)
class EvaluationDecision:
    task_id: str; decision: str; aggregate_score: float; blockers: tuple[str, ...] = (); warnings: tuple[str, ...] = (); rationale: str = ""; next_action: str = ""; policy_version: str = "default"
    def to_dict(self) -> dict[str, Any]:
        return {"task_id":self.task_id,"decision":self.decision,"aggregate_score":self.aggregate_score,"blockers":list(self.blockers),"warnings":list(self.warnings),"rationale":self.rationale,"next_action":self.next_action,"policy_version":self.policy_version}

@dataclass(frozen=True, slots=True)
class FeedbackPacket:
    task_id: str; rejected_criteria: tuple[str, ...] = (); missing_evidence: tuple[str, ...] = (); suggested_rework: tuple[str, ...] = (); escalation_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "rejected_criteria": list(self.rejected_criteria), "missing_evidence": list(self.missing_evidence), "suggested_rework": list(self.suggested_rework), "escalation_reason": self.escalation_reason}

    def __post_init__(self) -> None:
        object.__setattr__(self, "rejected_criteria", tuple(self.rejected_criteria))
        object.__setattr__(self, "missing_evidence", tuple(self.missing_evidence))
        object.__setattr__(self, "suggested_rework", tuple(self.suggested_rework))
