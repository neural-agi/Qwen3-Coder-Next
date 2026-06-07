"""Typed application settings definitions."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class EnvironmentName(StrEnum):
    """Supported application environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Immutable application settings for foundational infrastructure."""

    environment: EnvironmentName
    debug: bool
    workspace_root: Path
    artifacts_dir: Path
    data_dir: Path
    logs_dir: Path
