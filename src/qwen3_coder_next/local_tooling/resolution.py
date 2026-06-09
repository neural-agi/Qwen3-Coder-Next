"""Workspace resolution abstractions for the local tooling layer."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from qwen3_coder_next.local_tooling.contracts import WorkspaceContext


@dataclass(frozen=True, slots=True)
class WorkspaceResolutionRequest:
    """Immutable request for resolving workspace context."""

    request_id: str
    workspace_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkspaceResolutionResult:
    """Immutable result returned by a workspace resolver."""

    request_id: str
    workspace: WorkspaceContext | None
    resolved: bool
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkspaceResolver(ABC):
    """Abstract workspace resolution interface."""

    @abstractmethod
    def resolve(self, request: WorkspaceResolutionRequest) -> WorkspaceResolutionResult:
        """Resolve a workspace context for the supplied request."""


class StaticWorkspaceResolver(WorkspaceResolver):
    """Deterministic resolver that returns a fixed workspace context."""

    def __init__(self, workspace: WorkspaceContext | None = None) -> None:
        self._workspace = workspace

    def resolve(self, request: WorkspaceResolutionRequest) -> WorkspaceResolutionResult:
        """Return the configured workspace without filesystem discovery."""

        return WorkspaceResolutionResult(
            request_id=request.request_id,
            workspace=self._workspace,
            resolved=self._workspace is not None,
        )
