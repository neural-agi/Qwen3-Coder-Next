"""Workspace resolution abstractions for the local tooling layer."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
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


class RepositoryWorkspaceResolver(WorkspaceResolver):
    """Resolve a workspace from the actual repository layout."""

    def __init__(
        self,
        start_path: Path | None = None,
        repository_markers: tuple[str, ...] = (".git", "pyproject.toml", "README.md"),
    ) -> None:
        self._start_path = (start_path or Path.cwd()).resolve()
        self._repository_markers = repository_markers

    def resolve(self, request: WorkspaceResolutionRequest) -> WorkspaceResolutionResult:
        """Resolve the repository root and normalize any requested path."""

        repository_root = self._find_repository_root(self._start_path)
        if repository_root is None:
            return WorkspaceResolutionResult(
                request_id=request.request_id,
                workspace=None,
                resolved=False,
                metadata={"reason": "repository_root_not_found"},
            )

        requested_path = request.metadata.get("path")
        normalized_path = None
        if requested_path is not None:
            normalized_path = self._normalize_workspace_path(
                repository_root=repository_root,
                requested_path=Path(str(requested_path)),
            )
            if normalized_path is None:
                return WorkspaceResolutionResult(
                    request_id=request.request_id,
                    workspace=None,
                    resolved=False,
                    metadata={"reason": "path_outside_workspace"},
                )

        workspace = WorkspaceContext(
            workspace_id=request.workspace_id,
            root_path=repository_root,
            display_name=repository_root.name,
            metadata={
                **request.metadata,
                "repository_root": repository_root.as_posix(),
                **({"normalized_path": normalized_path.as_posix()} if normalized_path else {}),
            },
        )
        return WorkspaceResolutionResult(
            request_id=request.request_id,
            workspace=workspace,
            resolved=True,
            metadata={"repository_root": repository_root.as_posix()},
        )

    def _find_repository_root(self, start_path: Path) -> Path | None:
        current = start_path
        if current.is_file():
            current = current.parent
        for candidate in (current, *current.parents):
            if self._is_repository_root(candidate):
                return candidate
        return None

    def _is_repository_root(self, path: Path) -> bool:
        return any((path / marker).exists() for marker in self._repository_markers)

    def _normalize_workspace_path(
        self,
        repository_root: Path,
        requested_path: Path,
    ) -> Path | None:
        candidate = requested_path
        if not candidate.is_absolute():
            candidate = repository_root / candidate
        normalized = candidate.resolve(strict=False)
        try:
            normalized.relative_to(repository_root)
        except ValueError:
            return None
        return normalized


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
