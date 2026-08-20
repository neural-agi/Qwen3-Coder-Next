"""Deterministic global memory persistence with an explicit promotion gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from qwen3_coder_next.memory.exceptions import DuplicateMemoryError, MemoryNotFoundError
from qwen3_coder_next.memory.policies import (
    MemoryLifecycleActionType,
    MemoryLifecyclePlan,
)
from qwen3_coder_next.memory.serialization import MalformedMemorySerializedDataError
from qwen3_coder_next.memory.state import MemoryState
from qwen3_coder_next.memory.schemas import MemoryItem, MemoryTier


GLOBAL_MEMORY_STORE_SCHEMA_VERSION = 1


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MalformedMemorySerializedDataError(f"{name} must be a mapping.")
    return dict(value)


class GlobalMemoryStore:
    """Append-only global memory store requiring an explicit promotion plan."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self._storage_path = storage_path
        self._schema_version = GLOBAL_MEMORY_STORE_SCHEMA_VERSION
        self._states: dict[str, MemoryState] = {}
        self._load_from_disk()

    def create_global_state(self, state: MemoryState) -> MemoryState:
        """Create an empty or prevalidated global state."""

        self._ensure_global_state(state)
        if state.state_id in self._states:
            raise DuplicateMemoryError(f"Global state already exists for state_id={state.state_id!r}.")
        self._states[state.state_id] = state
        self._save_to_disk()
        return state

    def get_global_state(self, state_id: str) -> MemoryState:
        """Return a global state by stable identifier."""

        try:
            return self._states[state_id]
        except KeyError as exc:
            raise MemoryNotFoundError(f"Global state not found for state_id={state_id!r}.") from exc

    def promote_from_plan(self, plan: MemoryLifecyclePlan) -> MemoryState:
        """Apply only explicit project-to-global promotion actions from a plan."""

        if not isinstance(plan, MemoryLifecyclePlan):
            raise ValueError("plan must be a MemoryLifecyclePlan instance.")
        promotions = tuple(
            action
            for action in plan.actions
            if action.action is MemoryLifecycleActionType.PROMOTE
            and action.memory.tier is MemoryTier.PROJECT
            and action.target_tier is MemoryTier.GLOBAL
        )
        if not promotions:
            raise ValueError("plan contains no eligible project-to-global promotion.")
        state_id = f"global-{plan.state_id}"
        state = self._states.get(state_id, MemoryState(state_id=state_id))
        for action in promotions:
            promoted = MemoryItem(
                memory_id=action.memory.memory_id,
                tier=MemoryTier.GLOBAL,
                subject=action.memory.subject,
                content=action.memory.content,
                source=action.memory.source,
                timestamp=action.memory.timestamp,
                confidence=action.memory.confidence,
                tags=action.memory.tags,
                references=action.memory.references,
                schema_version=action.memory.schema_version,
            )
            if not any(item.memory_id == promoted.memory_id for item in state.memory_items):
                state = state.append_memory_item(promoted)
        self._states[state_id] = state
        self._save_to_disk()
        return state

    def list_global_states(self) -> list[MemoryState]:
        """Return global states in deterministic identifier order."""

        return [self._states[key] for key in sorted(self._states)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self._schema_version,
            "global_states": [state.to_dict() for state in self.list_global_states()],
        }

    def serialize(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GlobalMemoryStore":
        if not isinstance(payload, dict):
            raise MalformedMemorySerializedDataError("Global store payload must be a mapping.")
        entries = payload.get("global_states", ())
        if isinstance(entries, str):
            raise MalformedMemorySerializedDataError("global_states must not be a string.")
        store = cls(storage_path=None)
        store._schema_version = int(payload.get("schema_version", GLOBAL_MEMORY_STORE_SCHEMA_VERSION))
        for entry in entries:
            state = MemoryState.from_dict(_mapping(entry, "global_states entry"))
            store._ensure_global_state(state)
            store._states[state.state_id] = state
        return store

    @classmethod
    def deserialize(cls, payload: str | dict[str, Any]) -> "GlobalMemoryStore":
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise MalformedMemorySerializedDataError("Global store JSON is malformed.") from exc
        if not isinstance(payload, dict):
            raise MalformedMemorySerializedDataError("Global store payload must be a mapping.")
        return cls.from_dict(payload)

    def _load_from_disk(self) -> None:
        if self._storage_path is None or not self._storage_path.exists():
            return
        with self._storage_path.open("r", encoding="utf-8") as handle:
            loaded = self.from_dict(json.load(handle))
        self._states = loaded._states
        self._schema_version = loaded._schema_version

    def _save_to_disk(self) -> None:
        if self._storage_path is None:
            return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self._storage_path.open("w", encoding="utf-8") as handle:
            handle.write(self.serialize())

    @staticmethod
    def _ensure_global_state(state: MemoryState) -> None:
        if not isinstance(state, MemoryState):
            raise ValueError("state must be a MemoryState instance.")
        if any(item.tier is not MemoryTier.GLOBAL for item in state.memory_items):
            raise ValueError("global state may contain only global-tier memories.")

