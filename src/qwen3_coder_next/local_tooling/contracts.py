"""Foundational contracts for the local tooling layer."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    """Boundary policy for local tooling behavior."""

    allow_filesystem: bool = False
    allow_commands: bool = False
    allow_network: bool = False
    allowed_paths: tuple[Path, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkspaceContext:
    """Immutable workspace descriptor for local tooling requests."""

    workspace_id: str
    root_path: Path
    display_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RequestEnvelope:
    """Immutable request boundary for local tooling operations."""

    request_id: str
    workspace: WorkspaceContext
    operation: str
    policy: ExecutionPolicy
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResponseEnvelope:
    """Immutable response boundary for local tooling operations."""

    request_id: str
    success: bool
    status: str
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FileResult:
    """Immutable file-related result boundary."""

    path: Path
    exists: bool
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Immutable command-related result boundary."""

    command: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ArtifactDescriptor:
    """Immutable descriptor for local tooling artifacts."""

    artifact_id: str
    name: str
    location: Path
    artifact_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Immutable audit event boundary for local tooling."""

    event_id: str
    timestamp: datetime
    action: str
    subject: str
    details: dict[str, Any] = field(default_factory=dict)
