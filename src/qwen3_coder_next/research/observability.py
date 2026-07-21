"""Deterministic observability helpers for the Part 4 research pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping

from qwen3_coder_next.research.schemas import (
    RESEARCH_SCHEMA_VERSION,
    ResearchNextAction,
    ResearchStateStatus,
)


@dataclass(frozen=True, slots=True)
class ResearchStageTrace:
    """Traceable record for a single research stage transition."""

    stage_name: str
    event: str
    sequence_number: int
    source_count: int = 0
    evidence_count: int = 0
    detail: str = ""
    schema_version: int = RESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the stage trace into a deterministic mapping."""

        return {
            "stage_name": self.stage_name,
            "event": self.event,
            "sequence_number": self.sequence_number,
            "source_count": self.source_count,
            "evidence_count": self.evidence_count,
            "detail": self.detail,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResearchStageTrace":
        """Rehydrate a stage trace from serialized data."""

        return cls(
            stage_name=str(payload["stage_name"]),
            event=str(payload["event"]),
            sequence_number=int(payload["sequence_number"]),
            source_count=int(payload.get("source_count", 0)),
            evidence_count=int(payload.get("evidence_count", 0)),
            detail=str(payload.get("detail", "")),
            schema_version=int(payload.get("schema_version", RESEARCH_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class ResearchFlowMetrics:
    """Deterministic counters describing a research pipeline run."""

    executed_stage_count: int
    skipped_stage_count: int
    source_handle_count: int
    evidence_source_count: int
    normalized_evidence_count: int
    packet_evidence_count: int
    packet_confidence: float
    clarification_required: bool
    schema_version: int = RESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the pipeline metrics into a deterministic mapping."""

        return {
            "executed_stage_count": self.executed_stage_count,
            "skipped_stage_count": self.skipped_stage_count,
            "source_handle_count": self.source_handle_count,
            "evidence_source_count": self.evidence_source_count,
            "normalized_evidence_count": self.normalized_evidence_count,
            "packet_evidence_count": self.packet_evidence_count,
            "packet_confidence": self.packet_confidence,
            "clarification_required": self.clarification_required,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResearchFlowMetrics":
        """Rehydrate metrics from serialized data."""

        return cls(
            executed_stage_count=int(payload.get("executed_stage_count", 0)),
            skipped_stage_count=int(payload.get("skipped_stage_count", 0)),
            source_handle_count=int(payload.get("source_handle_count", 0)),
            evidence_source_count=int(payload.get("evidence_source_count", 0)),
            normalized_evidence_count=int(payload.get("normalized_evidence_count", 0)),
            packet_evidence_count=int(payload.get("packet_evidence_count", 0)),
            packet_confidence=float(payload.get("packet_confidence", 0.0)),
            clarification_required=bool(payload.get("clarification_required", False)),
            schema_version=int(payload.get("schema_version", RESEARCH_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class ResearchFailureRecord:
    """Structured explanation for a fallback or clarification path."""

    stage_name: str
    reason: str
    fallback_action: ResearchNextAction
    detail: str
    state_status: ResearchStateStatus = ResearchStateStatus.NEEDS_CLARIFICATION
    recorded_at: datetime = field(default_factory=lambda: datetime.fromtimestamp(0, UTC))
    schema_version: int = RESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the failure record into a deterministic mapping."""

        return {
            "stage_name": self.stage_name,
            "reason": self.reason,
            "fallback_action": self.fallback_action.value,
            "detail": self.detail,
            "state_status": self.state_status.value,
            "recorded_at": self.recorded_at.isoformat(),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResearchFailureRecord":
        """Rehydrate a failure record from serialized data."""

        return cls(
            stage_name=str(payload["stage_name"]),
            reason=str(payload["reason"]),
            fallback_action=ResearchNextAction(str(payload["fallback_action"])),
            detail=str(payload.get("detail", "")),
            state_status=ResearchStateStatus(
                str(payload.get("state_status", ResearchStateStatus.NEEDS_CLARIFICATION.value))
            ),
            recorded_at=datetime.fromisoformat(
                str(
                    payload.get(
                        "recorded_at",
                        datetime.fromtimestamp(0, UTC).isoformat(),
                    )
                )
            ),
            schema_version=int(payload.get("schema_version", RESEARCH_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class ResearchPipelineObservability:
    """Structured, inspectable metadata for a research pipeline run."""

    stage_transitions: tuple[ResearchStageTrace, ...]
    metrics: ResearchFlowMetrics
    fallback_decision: ResearchNextAction
    clarification_required: bool
    failure_record: ResearchFailureRecord | None = None
    schema_version: int = RESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the observability record into a deterministic mapping."""

        return {
            "stage_transitions": [item.to_dict() for item in self.stage_transitions],
            "metrics": self.metrics.to_dict(),
            "fallback_decision": self.fallback_decision.value,
            "clarification_required": self.clarification_required,
            "failure_record": self.failure_record.to_dict() if self.failure_record else None,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResearchPipelineObservability":
        """Rehydrate observability data from serialized data."""

        failure_record = payload.get("failure_record")
        return cls(
            stage_transitions=tuple(
                ResearchStageTrace.from_dict(item) for item in payload.get("stage_transitions", ())
            ),
            metrics=ResearchFlowMetrics.from_dict(dict(payload.get("metrics", {}))),
            fallback_decision=ResearchNextAction(
                str(payload.get("fallback_decision", ResearchNextAction.EXPAND_RESEARCH.value))
            ),
            clarification_required=bool(payload.get("clarification_required", False)),
            failure_record=ResearchFailureRecord.from_dict(dict(failure_record))
            if failure_record
            else None,
            schema_version=int(payload.get("schema_version", RESEARCH_SCHEMA_VERSION)),
        )

    @classmethod
    def empty(cls) -> "ResearchPipelineObservability":
        """Return the canonical empty observability snapshot."""

        return cls(
            stage_transitions=(),
            metrics=ResearchFlowMetrics(
                executed_stage_count=0,
                skipped_stage_count=0,
                source_handle_count=0,
                evidence_source_count=0,
                normalized_evidence_count=0,
                packet_evidence_count=0,
                packet_confidence=0.0,
                clarification_required=False,
            ),
            fallback_decision=ResearchNextAction.EXPAND_RESEARCH,
            clarification_required=False,
            failure_record=None,
        )
