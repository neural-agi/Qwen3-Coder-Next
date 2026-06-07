"""Model-facing contract definitions."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """Immutable request payload for future model adapters."""

    prompt: str
    system_prompt: str


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """Immutable response payload from a model adapter."""

    content: str
    model_name: str
    success: bool
