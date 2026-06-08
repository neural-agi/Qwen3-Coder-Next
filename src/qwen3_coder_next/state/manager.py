"""Stable API layer for task state management."""

from qwen3_coder_next.contracts import TaskState
from qwen3_coder_next.logging import get_logger
from qwen3_coder_next.state.store import StateStore


class StateManager:
    """Manage task state operations through a store and logger."""

    def __init__(self, store: StateStore | None = None) -> None:
        """Initialize the state manager with an in-memory store."""

        self._store = store or StateStore()
        self._logger = get_logger("qwen3_coder_next.state")

    def create_state(self, state: TaskState) -> TaskState:
        """Create and log a new task state."""

        self._logger.info("Creating state for task_id=%s", state.task_id)
        return self._store.create_state(state)

    def get_state(self, task_id: str) -> TaskState:
        """Retrieve and log a task state lookup."""

        self._logger.info("Retrieving state for task_id=%s", task_id)
        return self._store.get_state(task_id)

    def update_state(self, state: TaskState) -> TaskState:
        """Update and log an existing task state."""

        self._logger.info("Updating state for task_id=%s", state.task_id)
        return self._store.update_state(state)

    def delete_state(self, task_id: str) -> None:
        """Delete and log a task state."""

        self._logger.info("Deleting state for task_id=%s", task_id)
        self._store.delete_state(task_id)

    def list_states(self) -> list[TaskState]:
        """List and log all stored task states."""

        self._logger.info("Listing all task states")
        return self._store.list_states()
