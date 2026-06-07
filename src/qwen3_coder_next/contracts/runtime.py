"""Runtime contract definitions."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Immutable runtime configuration shared across modules."""

    environment: str
    debug: bool
    workspace_root: str
