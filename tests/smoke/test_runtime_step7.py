"""Smoke tests for Part 3 Step 7 runtime integration."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qwen3_coder_next.config import AppSettings, EnvironmentName
from qwen3_coder_next.contracts import TaskRequest
from qwen3_coder_next.execution import ExecutionResult, Executor
from qwen3_coder_next.logging import ApplicationLogger
from qwen3_coder_next.planning import PlanGraph, PlannerRequest, ValidationStatus
from qwen3_coder_next.runtime import Orchestrator, PlanningRuntimeResult


class RuntimeStep7SmokeTest(unittest.TestCase):
    """Verify planning is available through the existing runtime."""

    def _build_settings(self, workspace_root: Path) -> AppSettings:
        return AppSettings(
            environment=EnvironmentName.TESTING,
            debug=True,
            workspace_root=workspace_root,
            artifacts_dir=workspace_root / "artifacts",
            data_dir=workspace_root / "data",
            logs_dir=workspace_root / "logs",
        )

    def test_runtime_invokes_planner(self) -> None:
        """Invoke the planner through the runtime orchestration shell."""

        with TemporaryDirectory() as temp_dir:
            try:
                orchestrator = Orchestrator.initialize(self._build_settings(Path(temp_dir)))

                result = orchestrator.plan("Add planning runtime integration")

                self.assertIsInstance(result, PlanningRuntimeResult)
                self.assertIsInstance(result.pipeline.graph, PlanGraph)
                self.assertEqual(result.pipeline.validation_report.status, ValidationStatus.VALID)
            finally:
                ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")

    def test_planning_pipeline_integration(self) -> None:
        """Return planning output from the existing runtime boundary."""

        with TemporaryDirectory() as temp_dir:
            try:
                orchestrator = Orchestrator.initialize(self._build_settings(Path(temp_dir)))
                request = PlannerRequest(task_id="task-plan", user_goal="Plan runtime integration")

                result = orchestrator.plan(request)

                self.assertEqual(result.pipeline.request, request)
                self.assertIn('"task_id":"task-plan"', result.pipeline.serialized_request)
                self.assertIn('"step_id":"task-plan-step-1"', result.serialized_plan_graph)
                self.assertIsNotNone(orchestrator.last_planning_result)
            finally:
                ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")

    def test_runtime_receives_planning_output(self) -> None:
        """Ensure runtime execution captures the latest planning result."""

        with TemporaryDirectory() as temp_dir:
            try:
                orchestrator = Orchestrator.initialize(self._build_settings(Path(temp_dir)))
                executor = Executor(orchestrator)

                result = executor.execute(TaskRequest(task_id="task-runtime", objective="Runtime planning"))

                self.assertIsInstance(result, ExecutionResult)
                self.assertIsNotNone(orchestrator.last_planning_result)
                self.assertEqual(orchestrator.last_planning_result.pipeline.request.user_goal, "Runtime planning")
            finally:
                ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")

    def test_deterministic_integration_behavior(self) -> None:
        """Produce identical planning output for equivalent runtime inputs."""

        with TemporaryDirectory() as temp_dir:
            try:
                orchestrator = Orchestrator.initialize(self._build_settings(Path(temp_dir)))

                first = orchestrator.plan("Deterministic runtime planning")
                second = orchestrator.plan("Deterministic runtime planning")

                self.assertEqual(first, second)
                self.assertEqual(first.pipeline.graph, second.pipeline.graph)
                self.assertEqual(first.serialized_plan_graph, second.serialized_plan_graph)
            finally:
                ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")

    def test_existing_runtime_behavior_remains_unchanged(self) -> None:
        """Preserve the existing execution return value contract."""

        with TemporaryDirectory() as temp_dir:
            try:
                orchestrator = Orchestrator.initialize(self._build_settings(Path(temp_dir)))

                result = orchestrator.execute("existing-runtime-behavior")

                self.assertEqual(result, "Orchestration shell completed for task: existing-runtime-behavior")
            finally:
                ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")

    def test_backward_compatibility(self) -> None:
        """Continue to support the existing executor path."""

        with TemporaryDirectory() as temp_dir:
            try:
                orchestrator = Orchestrator.initialize(self._build_settings(Path(temp_dir)))
                executor = Executor(orchestrator)

                result = executor.execute("backward-compatibility")

                self.assertTrue(result.success)
                self.assertIsInstance(result, ExecutionResult)
            finally:
                ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")


if __name__ == "__main__":
    unittest.main(verbosity=2)
