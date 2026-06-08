"""Execution result contracts for the foundational task executor."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Immutable result returned by the task execution skeleton."""

    task_id: str
    success: bool
    summary: str
