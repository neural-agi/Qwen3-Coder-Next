"""Filesystem operation abstractions for the local tooling layer."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from qwen3_coder_next.local_tooling.contracts import WorkspaceContext
from qwen3_coder_next.local_tooling.filesystem import (
    DeterministicFileSystemService,
    FileSystemOperationRequest,
    FileSystemOperationResult,
    FileSystemService,
)


class FileSystemOperationType(StrEnum):
    """Supported filesystem operation types for the local tooling boundary."""

    READ = "read"
    WRITE = "write"
    EXISTS = "exists"


class FileMutationType(StrEnum):
    """Supported safe mutation types for the local tooling boundary."""

    ATOMIC_WRITE = "atomic_write"
    APPEND = "append"
    PATCH = "patch"


@dataclass(frozen=True, slots=True)
class FileSystemOperation:
    """Immutable operation descriptor for a filesystem operation."""

    operation_id: str
    operation_type: FileSystemOperationType
    path: Path
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FileSystemOperationOutcome:
    """Immutable outcome returned after executing a filesystem operation."""

    operation_id: str
    operation_type: FileSystemOperationType
    path: Path
    success: bool
    exists: bool
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FileMutationRequest:
    """Immutable request for a safe file mutation."""

    request_id: str
    workspace: WorkspaceContext
    path: Path | str
    mutation_type: FileMutationType
    content: str = ""
    expected_content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FileMutationPreflightResult:
    """Immutable preflight result for a safe file mutation."""

    request_id: str
    path: Path
    allowed: bool
    error_code: str = ""
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FileMutationResult:
    """Immutable result returned by a safe mutation service."""

    request_id: str
    path: Path
    mutation_type: FileMutationType
    success: bool
    content: str = ""
    previous_content: str = ""
    preflight: FileMutationPreflightResult | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class FileSystemOperator(ABC):
    """Abstract filesystem operation interface."""

    @abstractmethod
    def execute(self, operation: FileSystemOperation) -> FileSystemOperationOutcome:
        """Execute a filesystem operation."""


class DeterministicFileSystemOperator(FileSystemOperator):
    """Deterministic filesystem operator backed by the filesystem service boundary."""

    def __init__(
        self,
        service: FileSystemService | None = None,
    ) -> None:
        self._service = service or DeterministicFileSystemService()

    def execute(self, operation: FileSystemOperation) -> FileSystemOperationOutcome:
        """Dispatch the operation to the in-memory filesystem service."""

        request = FileSystemOperationRequest(
            request_id=operation.operation_id,
            path=operation.path,
            metadata=operation.metadata,
        )

        if operation.operation_type == FileSystemOperationType.READ:
            result = self._service.read(request)
            success = result.exists
        elif operation.operation_type == FileSystemOperationType.WRITE:
            result = self._service.write(request, operation.content)
            success = True
        else:
            result = self._service.exists(request)
            success = True

        return FileSystemOperationOutcome(
            operation_id=operation.operation_id,
            operation_type=operation.operation_type,
            path=result.path,
            success=success,
            exists=result.exists,
            content=result.content,
            metadata=operation.metadata,
        )


class FileMutationService(ABC):
    """Abstract safe file mutation interface."""

    @abstractmethod
    def preflight(self, request: FileMutationRequest) -> FileMutationPreflightResult:
        """Validate a mutation request before applying it."""

    @abstractmethod
    def apply(self, request: FileMutationRequest) -> FileMutationResult:
        """Apply a safe file mutation."""


class DeterministicFileMutationService(FileMutationService):
    """Deterministic in-memory safe mutation service."""

    def __init__(self, files: dict[Path, str] | None = None) -> None:
        self._files = dict(files or {})

    def preflight(self, request: FileMutationRequest) -> FileMutationPreflightResult:
        """Validate the request against the workspace boundary and input shape."""

        if not isinstance(request.path, (Path, str)):
            return self._reject(request.request_id, request.workspace.root_path, "unsupported_input", "Requested path must be a pathlib.Path or string value.")

        requested_text = str(request.path)
        if not requested_text or "\x00" in requested_text:
            return self._reject(request.request_id, request.workspace.root_path, "invalid_path", "Requested path is invalid.")

        resolved_path = self._resolve_path(request.workspace.root_path, Path(requested_text))
        if not self._is_within_workspace(request.workspace.root_path, resolved_path):
            return self._reject(request.request_id, resolved_path, "path_outside_workspace", "Requested path escapes the workspace boundary.")

        if request.mutation_type == FileMutationType.PATCH and not request.expected_content:
            return self._reject(request.request_id, resolved_path, "preflight_failed", "Patch requests must include expected_content.")

        return FileMutationPreflightResult(
            request_id=request.request_id,
            path=resolved_path,
            allowed=True,
            metadata=request.metadata,
        )

    def apply(self, request: FileMutationRequest) -> FileMutationResult:
        """Apply a deterministic atomic write, append, or patch operation."""

        preflight = self.preflight(request)
        if not preflight.allowed:
            return FileMutationResult(
                request_id=request.request_id,
                path=preflight.path,
                mutation_type=request.mutation_type,
                success=False,
                preflight=preflight,
                metadata=request.metadata,
            )

        current = self._files.get(preflight.path, "")
        if request.mutation_type == FileMutationType.ATOMIC_WRITE:
            updated = request.content
        elif request.mutation_type == FileMutationType.APPEND:
            updated = current + request.content
        else:
            if current != request.expected_content:
                rejected = FileMutationPreflightResult(
                    request_id=request.request_id,
                    path=preflight.path,
                    allowed=False,
                    error_code="preflight_failed",
                    error_message="Patch expected_content does not match current content.",
                    metadata=request.metadata,
                )
                return FileMutationResult(
                    request_id=request.request_id,
                    path=preflight.path,
                    mutation_type=request.mutation_type,
                    success=False,
                    previous_content=current,
                    preflight=rejected,
                    metadata=request.metadata,
                )
            updated = request.content

        self._files[preflight.path] = updated
        return FileMutationResult(
            request_id=request.request_id,
            path=preflight.path,
            mutation_type=request.mutation_type,
            success=True,
            content=updated,
            previous_content=current,
            preflight=preflight,
            metadata=request.metadata,
        )

    def _resolve_path(self, workspace_root: Path, requested_path: Path) -> Path:
        candidate = requested_path if requested_path.is_absolute() else workspace_root / requested_path
        return candidate.resolve(strict=False)

    def _is_within_workspace(self, workspace_root: Path, candidate: Path) -> bool:
        try:
            candidate.relative_to(workspace_root)
        except ValueError:
            return False
        return True

    def _reject(self, request_id: str, path: Path, code: str, message: str) -> FileMutationPreflightResult:
        return FileMutationPreflightResult(
            request_id=request_id,
            path=path,
            allowed=False,
            error_code=code,
            error_message=message,
        )
