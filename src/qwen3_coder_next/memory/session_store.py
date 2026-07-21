"""Deterministic session memory store for Part 5 Step 3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from qwen3_coder_next.memory.exceptions import DuplicateMemoryError, MemoryNotFoundError
from qwen3_coder_next.memory.schemas import MemoryItem, SessionSummary
from qwen3_coder_next.memory.serialization import MalformedMemorySerializedDataError
from qwen3_coder_next.memory.state import MemoryState


SESSION_MEMORY_STORE_SCHEMA_VERSION = 1


def _ensure_mapping(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MalformedMemorySerializedDataError(f"{field_name} must be a mapping.")
    return dict(value)


def _ensure_collection(value: object, field_name: str) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    if isinstance(value, str):
        raise MalformedMemorySerializedDataError(f"{field_name} must not be a string.")
    try:
        return tuple(value)  # type: ignore[arg-type]
    except TypeError as exc:  # pragma: no cover - defensive
        raise MalformedMemorySerializedDataError(f"{field_name} must be iterable.") from exc


class SessionMemoryStore:
    """Append-only session memory persistence backed by deterministic JSON."""

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize the session memory store."""

        self._storage_path = storage_path
        self._schema_version = SESSION_MEMORY_STORE_SCHEMA_VERSION
        self._session_states: dict[str, MemoryState] = {}
        self._load_from_disk()

    def create_session_state(self, state: MemoryState) -> MemoryState:
        """Create a new stored session state."""

        self._ensure_memory_state(state)
        if state.state_id in self._session_states:
            raise DuplicateMemoryError(f"Session state already exists for state_id={state.state_id!r}.")
        self._session_states[state.state_id] = state
        self._save_to_disk()
        return state

    def get_session_state(self, state_id: str) -> MemoryState:
        """Retrieve a stored session state by identifier."""

        try:
            return self._session_states[state_id]
        except KeyError as exc:
            raise MemoryNotFoundError(f"Session state not found for state_id={state_id!r}.") from exc

    def append_session_summary(self, state_id: str, session_summary: SessionSummary) -> MemoryState:
        """Append a session summary to a session-scoped memory state."""

        self._ensure_session_summary(session_summary)
        current_state = self._session_states.get(state_id, MemoryState(state_id=state_id))
        evolved_state = current_state.append_session_summary(session_summary)
        self._session_states[state_id] = evolved_state
        self._save_to_disk()
        return evolved_state

    def append_memory_item(self, state_id: str, memory_item: MemoryItem) -> MemoryState:
        """Append a memory item to a session-scoped memory state."""

        self._ensure_memory_item(memory_item)
        current_state = self._session_states.get(state_id, MemoryState(state_id=state_id))
        evolved_state = current_state.append_memory_item(memory_item)
        self._session_states[state_id] = evolved_state
        self._save_to_disk()
        return evolved_state

    def list_session_states(self) -> list[MemoryState]:
        """Return all session states in deterministic identifier order."""

        return [self._session_states[state_id] for state_id in sorted(self._session_states)]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the session store into a deterministic mapping."""

        return {
            "schema_version": self._schema_version,
            "session_states": [state.to_dict() for state in self.list_session_states()],
        }

    def serialize(self) -> str:
        """Serialize the session store into canonical JSON."""

        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SessionMemoryStore":
        """Rehydrate a session memory store from serialized data."""

        if not isinstance(payload, dict):
            raise MalformedMemorySerializedDataError("Session store payload must be a mapping.")

        schema_version = int(payload.get("schema_version", SESSION_MEMORY_STORE_SCHEMA_VERSION))
        session_states = _ensure_collection(payload.get("session_states"), "session_states")
        store = cls(storage_path=None)
        store._schema_version = schema_version
        store._session_states = {
            state.state_id: state
            for state in (
                cls._deserialize_state(item)
                for item in session_states
            )
        }
        return store

    @classmethod
    def deserialize(cls, payload: str | dict[str, Any]) -> "SessionMemoryStore":
        """Deserialize a session memory store from JSON or a mapping."""

        if isinstance(payload, str):
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError as exc:  # pragma: no cover - exercised in tests
                raise MalformedMemorySerializedDataError("Session store JSON is malformed.") from exc
        elif isinstance(payload, dict):
            parsed = payload
        else:
            raise MalformedMemorySerializedDataError(
                "Session store payload must be a JSON string or mapping."
            )

        if not isinstance(parsed, dict):
            raise MalformedMemorySerializedDataError(
                "Session store payload must decode to a mapping."
            )
        return cls.from_dict(parsed)

    def _load_from_disk(self) -> None:
        """Load stored session states from disk if configured."""

        if self._storage_path is None or not self._storage_path.exists():
            return
        with self._storage_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        loaded = self.from_dict(payload)
        self._session_states = loaded._session_states

    def _save_to_disk(self) -> None:
        """Persist session states to disk if configured."""

        if self._storage_path is None:
            return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self._storage_path.open("w", encoding="utf-8") as handle:
            handle.write(self.serialize())

    @staticmethod
    def _deserialize_state(payload: object) -> MemoryState:
        if not isinstance(payload, dict):
            raise MalformedMemorySerializedDataError("session_states entries must be mappings.")
        return MemoryState.from_dict(_ensure_mapping(payload, "session_states entry"))

    @staticmethod
    def _ensure_memory_state(state: MemoryState) -> None:
        if not isinstance(state, MemoryState):
            raise ValueError("state must be a MemoryState instance.")

    @staticmethod
    def _ensure_session_summary(session_summary: SessionSummary) -> None:
        if not isinstance(session_summary, SessionSummary):
            raise ValueError("session_summary must be a SessionSummary instance.")

    @staticmethod
    def _ensure_memory_item(memory_item: MemoryItem) -> None:
        if not isinstance(memory_item, MemoryItem):
            raise ValueError("memory_item must be a MemoryItem instance.")
