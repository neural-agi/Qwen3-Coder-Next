
"""Deterministic project memory store for Part 5 Step 4."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from qwen3_coder_next.memory.exceptions import DuplicateMemoryError, MemoryNotFoundError
from qwen3_coder_next.memory.schemas import ProjectDecision
from qwen3_coder_next.memory.serialization import MalformedMemorySerializedDataError
from qwen3_coder_next.memory.state import MemoryState


PROJECT_MEMORY_STORE_SCHEMA_VERSION = 1


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


def _normalize_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    if metadata is None:
        return {}
    return dict(metadata)


class ProjectMemoryStore:
    """Append-only project memory persistence backed by deterministic JSON."""

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize the project memory store."""

        self._storage_path = storage_path
        self._schema_version = PROJECT_MEMORY_STORE_SCHEMA_VERSION
        self._project_states: dict[str, MemoryState] = {}
        self._project_metadata: dict[str, dict[str, Any]] = {}
        self._load_from_disk()

    def create_project_state(
        self,
        state: MemoryState,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> MemoryState:
        """Create a new stored project state."""

        self._ensure_memory_state(state)
        self._ensure_project_identifier(state.state_id)
        if state.state_id in self._project_states:
            raise DuplicateMemoryError(
                f"Project state already exists for project_id={state.state_id!r}."
            )
        self._project_states[state.state_id] = state
        self._project_metadata[state.state_id] = _normalize_metadata(metadata)
        self._save_to_disk()
        return state

    def get_project_state(self, project_id: str) -> MemoryState:
        """Retrieve a stored project state by project identifier."""

        self._ensure_project_identifier(project_id)
        try:
            return self._project_states[project_id]
        except KeyError as exc:
            raise MemoryNotFoundError(f"Project state not found for project_id={project_id!r}.") from exc

    def get_project_metadata(self, project_id: str) -> dict[str, Any]:
        """Retrieve stored metadata for a project identifier."""

        self._ensure_project_identifier(project_id)
        try:
            return dict(self._project_metadata[project_id])
        except KeyError as exc:
            raise MemoryNotFoundError(f"Project metadata not found for project_id={project_id!r}.") from exc

    def append_project_decision(
        self,
        project_id: str,
        project_decision: ProjectDecision,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> MemoryState:
        """Append a project decision to a project-scoped memory state."""

        self._ensure_project_identifier(project_id)
        self._ensure_project_decision(project_decision)
        current_state = self._project_states.get(project_id, MemoryState(state_id=project_id))
        evolved_state = current_state.append_project_decision(project_decision)
        self._project_states[project_id] = evolved_state
        if metadata is not None:
            self._project_metadata[project_id] = _normalize_metadata(metadata)
        else:
            self._project_metadata.setdefault(project_id, {})
        self._save_to_disk()
        return evolved_state

    def list_project_states(self) -> list[MemoryState]:
        """Return all project states in deterministic identifier order."""

        return [self._project_states[project_id] for project_id in sorted(self._project_states)]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the project store into a deterministic mapping."""

        return {
            "schema_version": self._schema_version,
            "project_records": [self._project_record(project_id) for project_id in sorted(self._project_states)],
        }

    def serialize(self) -> str:
        """Serialize the project store into canonical JSON."""

        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProjectMemoryStore":
        """Rehydrate a project memory store from serialized data."""

        if not isinstance(payload, dict):
            raise MalformedMemorySerializedDataError("Project store payload must be a mapping.")

        schema_version = int(payload.get("schema_version", PROJECT_MEMORY_STORE_SCHEMA_VERSION))
        project_records = payload.get("project_records")
        project_states = payload.get("project_states")
        store = cls(storage_path=None)
        store._schema_version = schema_version
        store._project_states = {}
        store._project_metadata = {}
        if project_records is not None:
            records = _ensure_collection(project_records, "project_records")
            for record in records:
                project_id, state, metadata = cls._deserialize_record(record)
                store._project_states[project_id] = state
                store._project_metadata[project_id] = metadata
        elif project_states is not None:
            states = _ensure_collection(project_states, "project_states")
            for item in states:
                state = cls._deserialize_state(item)
                store._project_states[state.state_id] = state
                store._project_metadata[state.state_id] = {}
        return store

    @classmethod
    def deserialize(cls, payload: str | dict[str, Any]) -> "ProjectMemoryStore":
        """Deserialize a project memory store from JSON or a mapping."""

        if isinstance(payload, str):
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError as exc:  # pragma: no cover - exercised in tests
                raise MalformedMemorySerializedDataError("Project store JSON is malformed.") from exc
        elif isinstance(payload, dict):
            parsed = payload
        else:
            raise MalformedMemorySerializedDataError(
                "Project store payload must be a JSON string or mapping."
            )

        if not isinstance(parsed, dict):
            raise MalformedMemorySerializedDataError(
                "Project store payload must decode to a mapping."
            )
        return cls.from_dict(parsed)

    def _load_from_disk(self) -> None:
        """Load stored project states from disk if configured."""

        if self._storage_path is None or not self._storage_path.exists():
            return
        with self._storage_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        loaded = self.from_dict(payload)
        self._project_states = loaded._project_states
        self._project_metadata = loaded._project_metadata

    def _save_to_disk(self) -> None:
        """Persist project states to disk if configured."""

        if self._storage_path is None:
            return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self._storage_path.open("w", encoding="utf-8") as handle:
            handle.write(self.serialize())

    def _project_record(self, project_id: str) -> dict[str, Any]:
        state = self._project_states[project_id]
        return {
            "project_id": project_id,
            "metadata": dict(self._project_metadata.get(project_id, {})),
            "state": state.to_dict(),
        }

    @staticmethod
    def _deserialize_record(payload: object) -> tuple[str, MemoryState, dict[str, Any]]:
        record = _ensure_mapping(payload, "project_records entry")
        project_id = str(record["project_id"])
        state_payload = _ensure_mapping(record.get("state", record), "project state")
        state = MemoryState.from_dict(state_payload)
        if state.state_id != project_id:
            raise MalformedMemorySerializedDataError("project state identifier does not match project_id.")
        metadata = _normalize_metadata(record.get("metadata"))
        return project_id, state, metadata

    @staticmethod
    def _deserialize_state(payload: object) -> MemoryState:
        return MemoryState.from_dict(_ensure_mapping(payload, "project_states entry"))

    @staticmethod
    def _ensure_memory_state(state: MemoryState) -> None:
        if not isinstance(state, MemoryState):
            raise ValueError("state must be a MemoryState instance.")

    @staticmethod
    def _ensure_project_decision(project_decision: ProjectDecision) -> None:
        if not isinstance(project_decision, ProjectDecision):
            raise ValueError("project_decision must be a ProjectDecision instance.")

    @staticmethod
    def _ensure_project_identifier(project_id: object) -> None:
        if not isinstance(project_id, str) or not project_id.strip():
            raise ValueError("project_id must be a non-empty string.")
