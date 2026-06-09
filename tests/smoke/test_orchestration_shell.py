"""Smoke tests for the orchestration shell."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qwen3_coder_next.adapters import ModelGateway, StubModelAdapter
from qwen3_coder_next.artifacts import ArtifactManager
from qwen3_coder_next.config import AppSettings, EnvironmentName
from qwen3_coder_next.logging import ApplicationLogger
from qwen3_coder_next.memory import MemoryManager
from qwen3_coder_next.runtime import (
    RUNTIME_LOGGER_NAME,
    Orchestrator,
    RuntimeContext,
    create_runtime_context,
)
from qwen3_coder_next.state import StateManager


class OrchestrationShellSmokeTest(unittest.TestCase):
    """Verifies foundational orchestration shell behavior."""

    def _build_settings(self, workspace_root: Path) -> AppSettings:
        """Create test settings for the orchestration shell."""

        return AppSettings(
            environment=EnvironmentName.TESTING,
            debug=True,
            workspace_root=workspace_root,
            artifacts_dir=workspace_root / "artifacts",
            data_dir=workspace_root / "data",
            logs_dir=workspace_root / "logs",
        )

    def test_runtime_context_creation(self) -> None:
        """Create a runtime context with foundational service references."""

        with TemporaryDirectory() as temp_dir:
            settings = self._build_settings(Path(temp_dir))
            context = create_runtime_context(settings)

            self.assertIsInstance(context, RuntimeContext)
            self.assertIs(context.settings, settings)
            self.assertIsInstance(context.state_manager, StateManager)
            self.assertIsInstance(context.artifact_manager, ArtifactManager)
            self.assertIsInstance(context.memory_manager, MemoryManager)
            self.assertIsInstance(context.model_gateway, ModelGateway)
            self.assertEqual(context.logger.name, RUNTIME_LOGGER_NAME)
            ApplicationLogger.shutdown(RUNTIME_LOGGER_NAME)

    def test_orchestrator_creation(self) -> None:
        """Create an orchestrator from an explicit runtime context."""

        with TemporaryDirectory() as temp_dir:
            settings = self._build_settings(Path(temp_dir))
            logger = ApplicationLogger.initialize(settings, logger_name=RUNTIME_LOGGER_NAME)
            context = RuntimeContext(
                settings=settings,
                state_manager=StateManager(),
                artifact_manager=ArtifactManager(),
                memory_manager=MemoryManager(),
                model_gateway=ModelGateway(StubModelAdapter()),
                logger=logger,
            )

            orchestrator = Orchestrator(context)

            self.assertIs(orchestrator.context, context)
            ApplicationLogger.shutdown(RUNTIME_LOGGER_NAME)

    def test_execute_runs_successfully_and_logs(self) -> None:
        """Run placeholder execution and verify log messages are emitted."""

        with TemporaryDirectory() as temp_dir:
            settings = self._build_settings(Path(temp_dir))
            orchestrator = Orchestrator.initialize(settings)

            result = orchestrator.execute("foundation-smoke")

            for handler in orchestrator.context.logger.handlers:
                handler.flush()

            log_file = settings.logs_dir / "application.log"
            log_content = log_file.read_text(encoding="utf-8")

            self.assertEqual(
                result,
                "Orchestration shell completed for task: foundation-smoke",
            )
            self.assertIn("Orchestration execution started", log_content)
            self.assertIn("Orchestration execution finished", log_content)
            ApplicationLogger.shutdown(RUNTIME_LOGGER_NAME)


if __name__ == "__main__":
    print("Orchestration shell smoke tests passed.")
    unittest.main(verbosity=2)
