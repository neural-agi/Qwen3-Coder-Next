"""Smoke tests for the logging system."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qwen3_coder_next.config import AppSettings, EnvironmentName
from qwen3_coder_next.logging import ApplicationLogger, get_logger


class LoggingSystemSmokeTest(unittest.TestCase):
    """Verifies core logging infrastructure setup."""

    def test_logger_creation_and_handlers(self) -> None:
        """Create a logger with console and file handlers."""

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

            logger = ApplicationLogger.initialize(
                settings,
                logger_name="qwen3_coder_next.tests.logging.handlers",
            )

            self.assertIsInstance(logger, logging.Logger)
            self.assertEqual(len(logger.handlers), 2)
            self.assertTrue(
                any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers)
            )
            self.assertTrue(
                any(isinstance(handler, logging.FileHandler) for handler in logger.handlers)
            )
            ApplicationLogger.shutdown("qwen3_coder_next.tests.logging.handlers")

    def test_log_message_writing(self) -> None:
        """Write a log message and verify it reaches the log file."""

        with TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            settings = AppSettings(
                environment=EnvironmentName.TESTING,
                debug=False,
                workspace_root=workspace_root,
                artifacts_dir=workspace_root / "artifacts",
                data_dir=workspace_root / "data",
                logs_dir=workspace_root / "logs",
            )

            logger_name = "qwen3_coder_next.tests.logging.write"
            logger = ApplicationLogger.initialize(
                settings,
                logger_name=logger_name,
            )
            logger.info("Smoke test log message.")

            for handler in logger.handlers:
                handler.flush()

            log_file = settings.logs_dir / "application.log"
            self.assertTrue(log_file.exists())
            self.assertIn("Smoke test log message.", log_file.read_text(encoding="utf-8"))
            self.assertIs(get_logger(logger_name), logger)
            ApplicationLogger.shutdown(logger_name)


if __name__ == "__main__":
    print("Logging smoke tests passed.")
    unittest.main(verbosity=2)
