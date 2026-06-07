"""Task contract definitions."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TaskStatus(StrEnum):
    """Supported task lifecycle states."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TaskRequest:
    """Immutable request describing a task to be executed."""

    task_id: str
    objective: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TaskResult:
    """Immutable result produced by a completed task."""

    task_id: str
    success: bool
    summary: str
    outputs: dict[str, Any] = field(default_factory=dict)
