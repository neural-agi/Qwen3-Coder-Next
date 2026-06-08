"""Smoke tests for the in-memory state store."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qwen3_coder_next.config import AppSettings, EnvironmentName
from qwen3_coder_next.contracts import TaskState, TaskStatus
from qwen3_coder_next.logging import ApplicationLogger
from qwen3_coder_next.state import DuplicateStateError, StateManager, StateNotFoundError


class StateStoreSmokeTest(unittest.TestCase):
    """Verifies core state store lifecycle behavior."""

    def _build_state(self, task_id: str, status: TaskStatus) -> TaskState:
        """Create a task state instance for testing."""

        now = datetime.now(UTC)
        return TaskState(
            task_id=task_id,
            status=status,
            created_at=now,
            updated_at=now,
        )

    def test_state_lifecycle(self) -> None:
        """Create, retrieve, update, list, and delete state entries."""

        with TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            settings = AppSettings(
                environment=EnvironmentName.TESTING,
                debug=True,
                workspace_root=workspace_root,
                artifacts_dir=workspace_root / "artifacts",
                data_dir=workspace_root / "data",
                logs_dir=workspace_root / "logs",
            )
            ApplicationLogger.initialize(settings, logger_name="qwen3_coder_next.state")

            manager = StateManager()
            created_state = manager.create_state(self._build_state("task-001", TaskStatus.PENDING))

            retrieved_state = manager.get_state("task-001")
            self.assertEqual(retrieved_state, created_state)

            updated_state = TaskState(
                task_id="task-001",
                status=TaskStatus.RUNNING,
                created_at=created_state.created_at,
                updated_at=created_state.updated_at + timedelta(seconds=1),
            )
            manager.update_state(updated_state)

            states = manager.list_states()
            self.assertEqual(len(states), 1)
            self.assertEqual(states[0].status, TaskStatus.RUNNING)

            manager.delete_state("task-001")
            self.assertEqual(manager.list_states(), [])
            ApplicationLogger.shutdown("qwen3_coder_next.state")

    def test_duplicate_state_handling(self) -> None:
        """Raise when creating a duplicate state."""

        manager = StateManager()
        state = self._build_state("task-duplicate", TaskStatus.PENDING)
        manager.create_state(state)

        with self.assertRaises(DuplicateStateError):
            manager.create_state(state)

    def test_missing_state_handling(self) -> None:
        """Raise when reading, updating, or deleting a missing state."""

        manager = StateManager()
        missing_state = self._build_state("task-missing", TaskStatus.FAILED)

        with self.assertRaises(StateNotFoundError):
            manager.get_state("task-missing")

        with self.assertRaises(StateNotFoundError):
            manager.update_state(missing_state)

        with self.assertRaises(StateNotFoundError):
            manager.delete_state("task-missing")


if __name__ == "__main__":
    print("State store smoke tests passed.")
    unittest.main(verbosity=2)
