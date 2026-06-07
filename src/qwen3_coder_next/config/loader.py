"""Configuration loader with environment variable overrides."""

import os
from pathlib import Path

from qwen3_coder_next.config.defaults import (
    DEFAULT_ARTIFACTS_DIRNAME,
    DEFAULT_DATA_DIRNAME,
    DEFAULT_DEBUG,
    DEFAULT_ENVIRONMENT,
    DEFAULT_LOGS_DIRNAME,
    DEFAULT_WORKSPACE_ROOT,
)
from qwen3_coder_next.config.settings import AppSettings, EnvironmentName


ENVIRONMENT_KEY = "QWEN3_CODER_NEXT_ENVIRONMENT"
DEBUG_KEY = "QWEN3_CODER_NEXT_DEBUG"
WORKSPACE_ROOT_KEY = "QWEN3_CODER_NEXT_WORKSPACE_ROOT"
ARTIFACTS_DIR_KEY = "QWEN3_CODER_NEXT_ARTIFACTS_DIR"
DATA_DIR_KEY = "QWEN3_CODER_NEXT_DATA_DIR"
LOGS_DIR_KEY = "QWEN3_CODER_NEXT_LOGS_DIR"


def _load_environment() -> EnvironmentName:
    """Load the application environment from process variables."""

    raw_value = os.environ.get(ENVIRONMENT_KEY, DEFAULT_ENVIRONMENT)
    return EnvironmentName(raw_value)


def _load_debug() -> bool:
    """Load the debug flag from process variables."""

    raw_value = os.environ.get(DEBUG_KEY)
    if raw_value is None:
        return DEFAULT_DEBUG
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _load_workspace_root() -> Path:
    """Load the workspace root path from process variables."""

    raw_value = os.environ.get(WORKSPACE_ROOT_KEY)
    if raw_value is None:
        return DEFAULT_WORKSPACE_ROOT
    return Path(raw_value).expanduser().resolve()


def _load_path_override(key: str, default_name: str, workspace_root: Path) -> Path:
    """Load a configurable path relative to the workspace when unset."""

    raw_value = os.environ.get(key)
    if raw_value is None:
        return workspace_root / default_name
    return Path(raw_value).expanduser().resolve()


def load_settings() -> AppSettings:
    """Build application settings from defaults and environment overrides."""

    workspace_root = _load_workspace_root()
    return AppSettings(
        environment=_load_environment(),
        debug=_load_debug(),
        workspace_root=workspace_root,
        artifacts_dir=_load_path_override(
            ARTIFACTS_DIR_KEY,
            DEFAULT_ARTIFACTS_DIRNAME,
            workspace_root,
        ),
        data_dir=_load_path_override(
            DATA_DIR_KEY,
            DEFAULT_DATA_DIRNAME,
            workspace_root,
        ),
        logs_dir=_load_path_override(
            LOGS_DIR_KEY,
            DEFAULT_LOGS_DIRNAME,
            workspace_root,
        ),
    )


def get_settings() -> AppSettings:
    """Return the current application settings."""

    return load_settings()
