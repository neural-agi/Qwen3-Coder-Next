"""Smoke tests for runtime bootstrap integration."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qwen3_coder_next.bootstrap import BOOTSTRAP_LOGGER_NAME, RuntimeBootstrap
from qwen3_coder_next.config import AppSettings, EnvironmentName
from qwen3_coder_next.runtime import Orchestrator, RuntimeContext


class RuntimeBootstrapSmokeTest(unittest.TestCase):
    """Verifies foundational runtime bootstrap behavior."""

    def _build_settings(self, workspace_root: Path) -> AppSettings:
        """Create test settings for bootstrap integration."""

        return AppSettings(
            environment=EnvironmentName.TESTING,
            debug=True,
            workspace_root=workspace_root,
            artifacts_dir=workspace_root / "artifacts",
            data_dir=workspace_root / "data",
            logs_dir=workspace_root / "logs",
        )

    def test_runtime_bootstrap_creation(self) -> None:
        """Create a runtime bootstrap with foundational services."""

        with TemporaryDirectory() as temp_dir:
            settings = self._build_settings(Path(temp_dir))
            bootstrap = RuntimeBootstrap.initialize(settings)

            self.assertIs(bootstrap.settings, settings)
            self.assertEqual(bootstrap.logger.name, BOOTSTRAP_LOGGER_NAME)
            self.assertIsInstance(bootstrap.context, RuntimeContext)
            self.assertIsInstance(bootstrap.orchestrator, Orchestrator)
            bootstrap.shutdown()

    def test_startup_and_shutdown_logging(self) -> None:
        """Emit startup and shutdown logs through the bootstrap layer."""

        with TemporaryDirectory() as temp_dir:
            settings = self._build_settings(Path(temp_dir))
            bootstrap = RuntimeBootstrap.initialize(settings)

            bootstrap.startup()
            bootstrap.shutdown()

            log_file = settings.logs_dir / "application.log"
            log_content = log_file.read_text(encoding="utf-8")

            self.assertIn("Qwen3-Coder-Next Foundation Runtime Starting", log_content)
            self.assertIn("Repository Skeleton Loaded", log_content)
            self.assertIn("Shutdown Complete", log_content)
            self.assertIn(BOOTSTRAP_LOGGER_NAME, log_content)


if __name__ == "__main__":
    print("Runtime bootstrap smoke tests passed.")
    unittest.main(verbosity=2)
