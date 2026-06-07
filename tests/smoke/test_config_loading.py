"""Smoke tests for the configuration system."""

import os
from pathlib import Path
import unittest
from unittest.mock import patch

from qwen3_coder_next.config import EnvironmentName, get_settings
from qwen3_coder_next.config.defaults import (
    DEFAULT_ARTIFACTS_DIRNAME,
    DEFAULT_DATA_DIRNAME,
    DEFAULT_DEBUG,
    DEFAULT_LOGS_DIRNAME,
)
from qwen3_coder_next.config.loader import (
    ARTIFACTS_DIR_KEY,
    DATA_DIR_KEY,
    DEBUG_KEY,
    ENVIRONMENT_KEY,
    LOGS_DIR_KEY,
    WORKSPACE_ROOT_KEY,
)


class ConfigLoadingSmokeTest(unittest.TestCase):
    """Verifies default and environment-driven configuration loading."""

    def test_default_loading(self) -> None:
        """Load default settings when no overrides are present."""

        with patch.dict(os.environ, {}, clear=True):
            settings = get_settings()

        self.assertEqual(settings.environment, EnvironmentName.DEVELOPMENT)
        self.assertEqual(settings.debug, DEFAULT_DEBUG)
        self.assertEqual(settings.artifacts_dir, settings.workspace_root / DEFAULT_ARTIFACTS_DIRNAME)
        self.assertEqual(settings.data_dir, settings.workspace_root / DEFAULT_DATA_DIRNAME)
        self.assertEqual(settings.logs_dir, settings.workspace_root / DEFAULT_LOGS_DIRNAME)

    def test_environment_override_loading(self) -> None:
        """Load settings from environment variables."""

        override_env = {
            ENVIRONMENT_KEY: "testing",
            DEBUG_KEY: "true",
            WORKSPACE_ROOT_KEY: "D:/PARANJAY/Projects/Qwen-3-Coder-Next",
            ARTIFACTS_DIR_KEY: "D:/PARANJAY/Projects/Qwen-3-Coder-Next/custom-artifacts",
            DATA_DIR_KEY: "D:/PARANJAY/Projects/Qwen-3-Coder-Next/custom-data",
            LOGS_DIR_KEY: "D:/PARANJAY/Projects/Qwen-3-Coder-Next/custom-logs",
        }

        with patch.dict(os.environ, override_env, clear=True):
            settings = get_settings()

        self.assertEqual(settings.environment, EnvironmentName.TESTING)
        self.assertTrue(settings.debug)
        self.assertEqual(settings.workspace_root, Path(override_env[WORKSPACE_ROOT_KEY]).resolve())
        self.assertEqual(settings.artifacts_dir, Path(override_env[ARTIFACTS_DIR_KEY]).resolve())
        self.assertEqual(settings.data_dir, Path(override_env[DATA_DIR_KEY]).resolve())
        self.assertEqual(settings.logs_dir, Path(override_env[LOGS_DIR_KEY]).resolve())

    def test_path_fields_are_typed(self) -> None:
        """Ensure configured paths are exposed as Path objects."""

        with patch.dict(os.environ, {}, clear=True):
            settings = get_settings()

        self.assertIsInstance(settings.workspace_root, Path)
        self.assertIsInstance(settings.artifacts_dir, Path)
        self.assertIsInstance(settings.data_dir, Path)
        self.assertIsInstance(settings.logs_dir, Path)


if __name__ == "__main__":
    print("Configuration smoke tests passed.")
    unittest.main(verbosity=2)
