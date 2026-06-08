"""Dictionary-backed in-memory state storage."""

from qwen3_coder_next.contracts import TaskState
from qwen3_coder_next.state.exceptions import DuplicateStateError, StateNotFoundError


class StateStore:
    """In-memory store for task lifecycle state."""

    def __init__(self) -> None:
        """Initialize the in-memory state store."""

        self._states: dict[str, TaskState] = {}

    def create_state(self, state: TaskState) -> TaskState:
        """Create a new task state entry."""

        if state.task_id in self._states:
            raise DuplicateStateError(f"State already exists for task_id={state.task_id!r}.")
        self._states[state.task_id] = state
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
        return state

    def delete_state(self, task_id: str) -> None:
        """Delete a stored task state by task identifier."""

        if task_id not in self._states:
            raise StateNotFoundError(f"State not found for task_id={task_id!r}.")
        del self._states[task_id]

    def list_states(self) -> list[TaskState]:
        """Return all stored task states."""

        return list(self._states.values())
