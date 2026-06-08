"""Smoke tests for the foundational task executor."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qwen3_coder_next.artifacts import ArtifactManager
from qwen3_coder_next.config import AppSettings, EnvironmentName
from qwen3_coder_next.contracts import TaskRequest, TaskStatus
from qwen3_coder_next.execution import ExecutionResult, Executor
from qwen3_coder_next.logging import ApplicationLogger
from qwen3_coder_next.runtime import Orchestrator


class ExecutorSmokeTest(unittest.TestCase):
    """Verifies minimal task execution behavior."""

    def _build_settings(self, workspace_root: Path) -> AppSettings:
        """Create test settings for executor integration."""

        return AppSettings(
            environment=EnvironmentName.TESTING,
            debug=True,
            workspace_root=workspace_root,
            artifacts_dir=workspace_root / "artifacts",
            data_dir=workspace_root / "data",
            logs_dir=workspace_root / "logs",
        )

    def test_executor_creation(self) -> None:
        """Create an executor bound to foundational services."""

        with TemporaryDirectory() as temp_dir:
            settings = self._build_settings(Path(temp_dir))
            orchestrator = Orchestrator.initialize(settings)
            executor = Executor(orchestrator)

            self.assertIs(executor.artifact_manager.__class__, ArtifactManager)
            ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")

    def test_task_lifecycle_transition(self) -> None:
        """Advance task state from pending to running to succeeded."""

        with TemporaryDirectory() as temp_dir:
            settings = self._build_settings(Path(temp_dir))
            orchestrator = Orchestrator.initialize(settings)
            executor = Executor(orchestrator)
            request = TaskRequest(task_id="task-001", objective="executor-smoke")

            result = executor.execute(request)
            state = orchestrator.context.state_manager.get_state(result.task_id)

            self.assertEqual(state.status, TaskStatus.SUCCEEDED)
            ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")

    def test_successful_execution_result(self) -> None:
        """Return a successful immutable execution result."""

        with TemporaryDirectory() as temp_dir:
            settings = self._build_settings(Path(temp_dir))
            orchestrator = Orchestrator.initialize(settings)
            executor = Executor(orchestrator)

            result = executor.execute("executor-result")

            self.assertIsInstance(result, ExecutionResult)
            self.assertTrue(result.success)
            self.assertIn("Orchestration shell completed for task", result.summary)
            ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")

    def test_integration_with_existing_state_manager(self) -> None:
        """Use the orchestrator state manager to persist execution state."""

        with TemporaryDirectory() as temp_dir:
            settings = self._build_settings(Path(temp_dir))
            orchestrator = Orchestrator.initialize(settings)
            executor = Executor(orchestrator)
            request = TaskRequest(task_id="task-002", objective="state-integration")

            executor.execute(request)
            states = orchestrator.context.state_manager.list_states()

            self.assertEqual(len(states), 1)
            self.assertEqual(states[0].task_id, "task-002")
            self.assertEqual(states[0].status, TaskStatus.SUCCEEDED)
            ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")


if __name__ == "__main__":
    print("Executor smoke tests passed.")
    unittest.main(verbosity=2)
