"""Planning contracts shared across the codebase."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from qwen3_coder_next.planning.schemas import PlanStep


class PlanStatus(StrEnum):
    """Supported planning lifecycle states."""

    DRAFT = "draft"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PlanRequest:
    """Immutable request for generating a plan."""

    request_id: str
    objective: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PlanResult:
    """Immutable result returned by a planner."""

    request_id: str
    status: PlanStatus
    summary: str
    steps: tuple[PlanStep, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
