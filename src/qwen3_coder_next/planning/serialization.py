"""Deterministic planning artifact serialization for Part 3 Step 6."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from qwen3_coder_next.planning.schemas import (
    PlanDraft,
    PlanGraph,
    PlannerRequest,
    ValidationReport,
)
from qwen3_coder_next.planning.state import PlannerState


PlanningSerializable = PlannerRequest | PlanDraft | PlanGraph | ValidationReport | PlannerState
TPlanningSerializable = TypeVar("TPlanningSerializable", bound=PlanningSerializable)


class PlanningSerializationError(ValueError):
    """Base error for planning serialization failures."""


class MalformedPlanningSerializedDataError(PlanningSerializationError):
    """Raised when serialized planning data cannot be decoded."""


@dataclass(frozen=True, slots=True)
class PlanningArtifactSerializer:
    """Serialize planning artifacts into stable JSON and rehydrate them back."""

    def serialize(self, item: PlanningSerializable) -> str:
        """Serialize a planning artifact into canonical JSON."""

        if isinstance(item, PlannerRequest):
            payload = item.to_dict()
        elif isinstance(item, PlanDraft):
            payload = item.to_dict()
        elif isinstance(item, PlanGraph):
            payload = item.to_dict()
        elif isinstance(item, ValidationReport):
            payload = item.to_dict()
        elif isinstance(item, PlannerState):
            payload = item.to_dict()
        else:
            raise PlanningSerializationError(
                f"Unsupported planning artifact type: {type(item)!r}"
            )
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def deserialize_request(self, payload: str | dict[str, Any]) -> PlannerRequest:
        """Deserialize a planner request."""

        return self._deserialize(payload, PlannerRequest.from_dict)

    def deserialize_draft(self, payload: str | dict[str, Any]) -> PlanDraft:
        """Deserialize a plan draft."""

        return self._deserialize(payload, PlanDraft.from_dict)

    def deserialize_graph(self, payload: str | dict[str, Any]) -> PlanGraph:
        """Deserialize a plan graph."""

        return self._deserialize(payload, PlanGraph.from_dict)

    def deserialize_report(self, payload: str | dict[str, Any]) -> ValidationReport:
        """Deserialize a validation report."""

        return self._deserialize(payload, ValidationReport.from_dict)

    def deserialize_state(self, payload: str | dict[str, Any]) -> PlannerState:
        """Deserialize planner state."""

        return self._deserialize(payload, PlannerState.from_dict)

    def _deserialize(
        self,
        payload: str | dict[str, Any],
        loader: Callable[[dict[str, Any]], TPlanningSerializable],
    ) -> TPlanningSerializable:
        if isinstance(payload, str):
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError as exc:  # pragma: no cover - exercised via smoke tests
                raise MalformedPlanningSerializedDataError(
                    "Planning artifact JSON is malformed."
                ) from exc
        elif isinstance(payload, dict):
            parsed = payload
        else:
            raise MalformedPlanningSerializedDataError(
                "Planning artifact payload must be a JSON string or mapping."
            )

        if not isinstance(parsed, dict):
            raise MalformedPlanningSerializedDataError(
                "Planning artifact payload must decode to a mapping."
            )
        try:
            return loader(dict(parsed))
        except (KeyError, TypeError, ValueError) as exc:
            raise MalformedPlanningSerializedDataError(
                "Planning artifact payload is missing required fields."
            ) from exc


_DEFAULT_SERIALIZER = PlanningArtifactSerializer()


def serialize_planner_request(request: PlannerRequest) -> str:
    """Serialize a planner request into canonical JSON."""

    return _DEFAULT_SERIALIZER.serialize(request)


def serialize_plan_draft(draft: PlanDraft) -> str:
    """Serialize a plan draft into canonical JSON."""

    return _DEFAULT_SERIALIZER.serialize(draft)


def serialize_plan_graph(graph: PlanGraph) -> str:
    """Serialize a plan graph into canonical JSON."""

    return _DEFAULT_SERIALIZER.serialize(graph)


def serialize_validation_report(report: ValidationReport) -> str:
    """Serialize a validation report into canonical JSON."""

    return _DEFAULT_SERIALIZER.serialize(report)


def serialize_planner_state(state: PlannerState) -> str:
    """Serialize planner state into canonical JSON."""

    return _DEFAULT_SERIALIZER.serialize(state)


def deserialize_planner_request(payload: str | dict[str, Any]) -> PlannerRequest:
    """Deserialize a planner request from canonical JSON or a mapping."""

    return _DEFAULT_SERIALIZER.deserialize_request(payload)


def deserialize_plan_draft(payload: str | dict[str, Any]) -> PlanDraft:
    """Deserialize a plan draft from canonical JSON or a mapping."""

    return _DEFAULT_SERIALIZER.deserialize_draft(payload)


def deserialize_plan_graph(payload: str | dict[str, Any]) -> PlanGraph:
    """Deserialize a plan graph from canonical JSON or a mapping."""

    return _DEFAULT_SERIALIZER.deserialize_graph(payload)


def deserialize_validation_report(payload: str | dict[str, Any]) -> ValidationReport:
    """Deserialize a validation report from canonical JSON or a mapping."""

    return _DEFAULT_SERIALIZER.deserialize_report(payload)


def deserialize_planner_state(payload: str | dict[str, Any]) -> PlannerState:
    """Deserialize planner state from canonical JSON or a mapping."""

    return _DEFAULT_SERIALIZER.deserialize_state(payload)
