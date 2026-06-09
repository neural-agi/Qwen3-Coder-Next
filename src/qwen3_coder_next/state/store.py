"""Dictionary-backed state storage with optional filesystem persistence."""

import json
from pathlib import Path

from qwen3_coder_next.contracts import TaskState
from qwen3_coder_next.state.exceptions import DuplicateStateError, StateNotFoundError


class StateStore:
    """Store for task lifecycle state."""

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize the state store."""

        self._storage_path = storage_path
        self._states: dict[str, TaskState] = {}
        self._load_from_disk()

    def create_state(self, state: TaskState) -> TaskState:
        """Create a new task state entry."""

        if state.task_id in self._states:
            raise DuplicateStateError(f"State already exists for task_id={state.task_id!r}.")
        self._states[state.task_id] = state
        self._save_to_disk()
        return state

    def get_state(self, task_id: str) -> TaskState:
        """Return a stored task state by task identifier."""

        try:
            return self._states[task_id]
        except KeyError as exc:
            raise StateNotFoundError(f"State not found for task_id={task_id!r}.") from exc

    def update_state(self, state: TaskState) -> TaskState:
        """Replace an existing task state entry."""

        if state.task_id not in self._states:
            raise StateNotFoundError(f"State not found for task_id={state.task_id!r}.")
        self._states[state.task_id] = state
        self._save_to_disk()
        return state

    def delete_state(self, task_id: str) -> None:
        """Delete a stored task state by task identifier."""

        if task_id not in self._states:
            raise StateNotFoundError(f"State not found for task_id={task_id!r}.")
        del self._states[task_id]
        self._save_to_disk()

    def list_states(self) -> list[TaskState]:
        """Return all stored task states."""

        return list(self._states.values())

    def _load_from_disk(self) -> None:
        """Load persisted state entries if a storage path is configured."""

        if self._storage_path is None or not self._storage_path.exists():
            return

        with self._storage_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        self._states = {
            item["task_id"]: self._deserialize_state(item)
            for item in payload
        }

    def _save_to_disk(self) -> None:
        """Persist state entries if a storage path is configured."""

        if self._storage_path is None:
            return

        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self._storage_path.open("w", encoding="utf-8") as handle:
            json.dump([self._serialize_state(state) for state in self._states.values()], handle, indent=2)

    def _serialize_state(self, state: TaskState) -> dict[str, object]:
        return {
            "task_id": state.task_id,
            "status": state.status.value,
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
        }

    def _deserialize_state(self, payload: dict[str, object]) -> TaskState:
        from datetime import datetime

        from qwen3_coder_next.contracts import TaskStatus

        return TaskState(
            task_id=str(payload["task_id"]),
            status=TaskStatus(str(payload["status"])),
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            updated_at=datetime.fromisoformat(str(payload["updated_at"])),
        )
