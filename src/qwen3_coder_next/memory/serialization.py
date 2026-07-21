"""Deterministic serialization helpers for memory contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from qwen3_coder_next.memory.schemas import (
    GlobalPattern,
    MemoryEvent,
    MemoryItem,
    MemoryQuery,
    MemoryResult,
    MemoryTier,
    ProjectDecision,
    RetentionPolicy,
    SessionSummary,
)
from qwen3_coder_next.memory.state import MemoryRevision, MemoryState


MemorySerializable = (
    MemoryItem
    | MemoryQuery
    | MemoryResult
    | SessionSummary
    | ProjectDecision
    | GlobalPattern
    | MemoryEvent
    | RetentionPolicy
    | MemoryRevision
    | MemoryState
)
TMemorySerializable = TypeVar("TMemorySerializable", bound=MemorySerializable)


class MemorySerializationError(ValueError):
    """Base error for memory serialization failures."""


class MalformedMemorySerializedDataError(MemorySerializationError):
    """Raised when serialized memory data cannot be decoded."""


@dataclass(frozen=True, slots=True)
class MemorySerializer:
    """Serialize memory artifacts into stable JSON and rehydrate them back."""

    def serialize(self, item: MemorySerializable) -> str:
        """Serialize a memory artifact into canonical JSON."""

        if isinstance(item, MemoryItem):
            payload = item.to_dict()
        elif isinstance(item, MemoryQuery):
            payload = item.to_dict()
        elif isinstance(item, MemoryResult):
            payload = item.to_dict()
        elif isinstance(item, SessionSummary):
            payload = item.to_dict()
        elif isinstance(item, ProjectDecision):
            payload = item.to_dict()
        elif isinstance(item, GlobalPattern):
            payload = item.to_dict()
        elif isinstance(item, MemoryEvent):
            payload = item.to_dict()
        elif isinstance(item, RetentionPolicy):
            payload = item.to_dict()
        elif isinstance(item, MemoryRevision):
            payload = item.to_dict()
        elif isinstance(item, MemoryState):
            payload = item.to_dict()
        else:
            raise MemorySerializationError(f"Unsupported memory artifact type: {type(item)!r}")
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def deserialize_item(self, payload: str | dict[str, Any]) -> MemoryItem:
        """Deserialize a memory item."""

        return self._deserialize(payload, MemoryItem.from_dict)

    def deserialize_query(self, payload: str | dict[str, Any]) -> MemoryQuery:
        """Deserialize a memory query."""

        return self._deserialize(payload, MemoryQuery.from_dict)

    def deserialize_result(self, payload: str | dict[str, Any]) -> MemoryResult:
        """Deserialize a memory result."""

        return self._deserialize(payload, MemoryResult.from_dict)

    def deserialize_session_summary(self, payload: str | dict[str, Any]) -> SessionSummary:
        """Deserialize a session summary."""

        return self._deserialize(payload, SessionSummary.from_dict)

    def deserialize_project_decision(self, payload: str | dict[str, Any]) -> ProjectDecision:
        """Deserialize a project decision."""

        return self._deserialize(payload, ProjectDecision.from_dict)

    def deserialize_global_pattern(self, payload: str | dict[str, Any]) -> GlobalPattern:
        """Deserialize a global pattern."""

        return self._deserialize(payload, GlobalPattern.from_dict)

    def deserialize_memory_event(self, payload: str | dict[str, Any]) -> MemoryEvent:
        """Deserialize a memory event."""

        return self._deserialize(payload, MemoryEvent.from_dict)

    def deserialize_retention_policy(self, payload: str | dict[str, Any]) -> RetentionPolicy:
        """Deserialize a retention policy."""

        return self._deserialize(payload, RetentionPolicy.from_dict)

    def deserialize_revision(self, payload: str | dict[str, Any]) -> MemoryRevision:
        """Deserialize a memory revision."""

        return self._deserialize(payload, MemoryRevision.from_dict)

    def deserialize_state(self, payload: str | dict[str, Any]) -> MemoryState:
        """Deserialize memory state."""

        return self._deserialize(payload, MemoryState.from_dict)

    def _deserialize(
        self,
        payload: str | dict[str, Any],
        loader: Callable[[dict[str, Any]], TMemorySerializable],
    ) -> TMemorySerializable:
        if isinstance(payload, str):
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError as exc:  # pragma: no cover - exercised via tests
                raise MalformedMemorySerializedDataError(
                    "Memory artifact JSON is malformed."
                ) from exc
        elif isinstance(payload, dict):
            parsed = payload
        else:
            raise MalformedMemorySerializedDataError(
                "Memory artifact payload must be a JSON string or mapping."
            )

        if not isinstance(parsed, dict):
            raise MalformedMemorySerializedDataError(
                "Memory artifact payload must decode to a mapping."
            )
        try:
            return loader(dict(parsed))
        except (KeyError, TypeError, ValueError) as exc:
            raise MalformedMemorySerializedDataError(
                "Memory artifact payload is missing required fields."
            ) from exc


_DEFAULT_SERIALIZER = MemorySerializer()


def serialize_memory_item(item: MemoryItem) -> str:
    """Serialize a memory item into canonical JSON."""

    return _DEFAULT_SERIALIZER.serialize(item)


def serialize_memory_query(query: MemoryQuery) -> str:
    """Serialize a memory query into canonical JSON."""

    return _DEFAULT_SERIALIZER.serialize(query)


def serialize_memory_result(result: MemoryResult) -> str:
    """Serialize a memory result into canonical JSON."""

    return _DEFAULT_SERIALIZER.serialize(result)


def serialize_session_summary(summary: SessionSummary) -> str:
    """Serialize a session summary into canonical JSON."""

    return _DEFAULT_SERIALIZER.serialize(summary)


def serialize_project_decision(decision: ProjectDecision) -> str:
    """Serialize a project decision into canonical JSON."""

    return _DEFAULT_SERIALIZER.serialize(decision)


def serialize_global_pattern(pattern: GlobalPattern) -> str:
    """Serialize a global pattern into canonical JSON."""

    return _DEFAULT_SERIALIZER.serialize(pattern)


def serialize_memory_event(event: MemoryEvent) -> str:
    """Serialize a memory event into canonical JSON."""

    return _DEFAULT_SERIALIZER.serialize(event)


def serialize_retention_policy(policy: RetentionPolicy) -> str:
    """Serialize a retention policy into canonical JSON."""

    return _DEFAULT_SERIALIZER.serialize(policy)


def serialize_memory_revision(revision: MemoryRevision) -> str:
    """Serialize a memory revision into canonical JSON."""

    return _DEFAULT_SERIALIZER.serialize(revision)


def serialize_memory_state(state: MemoryState) -> str:
    """Serialize memory state into canonical JSON."""

    return _DEFAULT_SERIALIZER.serialize(state)


def deserialize_memory_item(payload: str | dict[str, Any]) -> MemoryItem:
    """Deserialize a memory item from canonical JSON or a mapping."""

    return _DEFAULT_SERIALIZER.deserialize_item(payload)


def deserialize_memory_query(payload: str | dict[str, Any]) -> MemoryQuery:
    """Deserialize a memory query from canonical JSON or a mapping."""

    return _DEFAULT_SERIALIZER.deserialize_query(payload)


def deserialize_memory_result(payload: str | dict[str, Any]) -> MemoryResult:
    """Deserialize a memory result from canonical JSON or a mapping."""

    return _DEFAULT_SERIALIZER.deserialize_result(payload)


def deserialize_session_summary(payload: str | dict[str, Any]) -> SessionSummary:
    """Deserialize a session summary from canonical JSON or a mapping."""

    return _DEFAULT_SERIALIZER.deserialize_session_summary(payload)


def deserialize_project_decision(payload: str | dict[str, Any]) -> ProjectDecision:
    """Deserialize a project decision from canonical JSON or a mapping."""

    return _DEFAULT_SERIALIZER.deserialize_project_decision(payload)


def deserialize_global_pattern(payload: str | dict[str, Any]) -> GlobalPattern:
    """Deserialize a global pattern from canonical JSON or a mapping."""

    return _DEFAULT_SERIALIZER.deserialize_global_pattern(payload)


def deserialize_memory_event(payload: str | dict[str, Any]) -> MemoryEvent:
    """Deserialize a memory event from canonical JSON or a mapping."""

    return _DEFAULT_SERIALIZER.deserialize_memory_event(payload)


def deserialize_retention_policy(payload: str | dict[str, Any]) -> RetentionPolicy:
    """Deserialize a retention policy from canonical JSON or a mapping."""

    return _DEFAULT_SERIALIZER.deserialize_retention_policy(payload)


def deserialize_memory_revision(payload: str | dict[str, Any]) -> MemoryRevision:
    """Deserialize a memory revision from canonical JSON or a mapping."""

    return _DEFAULT_SERIALIZER.deserialize_revision(payload)


def deserialize_memory_state(payload: str | dict[str, Any]) -> MemoryState:
    """Deserialize memory state from canonical JSON or a mapping."""

    return _DEFAULT_SERIALIZER.deserialize_state(payload)

