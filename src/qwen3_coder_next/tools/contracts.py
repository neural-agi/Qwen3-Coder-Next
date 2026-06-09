"""Tool contracts shared across the codebase."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ToolStatus(StrEnum):
    """Supported tool lifecycle states."""

    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Immutable description of a tool."""

    tool_id: str
    name: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolRequest:
    """Immutable request sent to a tool."""

    tool_name: str
    input: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Immutable result returned by a tool."""

    tool_name: str
    status: ToolStatus
    output: str
    metadata: dict[str, Any] = field(default_factory=dict)
