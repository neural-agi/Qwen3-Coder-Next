"""State contract definitions."""

from dataclasses import dataclass
from datetime import datetime

from qwen3_coder_next.contracts.task import TaskStatus


@dataclass(frozen=True, slots=True)
class MessageRecord:
    """Immutable record of a runtime message."""

    role: str
    content: str
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class TaskState:
    """Immutable snapshot of task lifecycle state."""

    task_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
