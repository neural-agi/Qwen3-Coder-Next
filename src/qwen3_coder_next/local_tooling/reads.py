"""Safe file read abstractions for the local tooling layer."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any

from qwen3_coder_next.local_tooling.contracts import WorkspaceContext


class FileReadErrorCode(StrEnum):
    """Structured error codes for safe file reads."""

    INVALID_PATH = "invalid_path"
    PATH_OUTSIDE_WORKSPACE = "path_outside_workspace"
    FILE_NOT_FOUND = "file_not_found"
    UNSUPPORTED_INPUT = "unsupported_input"


@dataclass(frozen=True, slots=True)
class FileReadRequest:
    """Immutable request for a safe file read."""

    request_id: str
    workspace: WorkspaceContext
    path: Path | str
    preview_length: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FileReadResult:
    """Immutable result returned by a safe file read service."""

    request_id: str
    path: Path
    success: bool
    content: str = ""
    preview: str = ""
    digest: str = ""
    error_code: FileReadErrorCode | None = None
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class FileReadService(ABC):
    """Abstract safe file read interface."""

    @abstractmethod
    def read(self, request: FileReadRequest) -> FileReadResult:
        """Read a file from within a workspace boundary."""


class DeterministicFileReadService(FileReadService):
    """Deterministic in-memory safe file read service."""

    def __init__(self, files: dict[Path, str] | None = None) -> None:
        self._files = {path: content for path, content in (files or {}).items()}

    def read(self, request: FileReadRequest) -> FileReadResult:
        """Return file content, preview, and digest without touching disk."""

        validation_error = self._validate_path(
            request.request_id,
            request.workspace.root_path,
            request.path,
        )
        if validation_error is not None:
            return validation_error

        absolute_path = self._normalize_path(request.workspace.root_path, Path(str(request.path)))
        if not self._is_within_workspace(request.workspace.root_path, absolute_path):
            return FileReadResult(
                request_id=request.request_id,
                path=absolute_path,
                success=False,
                error_code=FileReadErrorCode.PATH_OUTSIDE_WORKSPACE,
                error_message="Requested path escapes the workspace boundary.",
                metadata=request.metadata,
            )
        if absolute_path not in self._files:
            return FileReadResult(
                request_id=request.request_id,
                path=absolute_path,
                success=False,
                error_code=FileReadErrorCode.FILE_NOT_FOUND,
                error_message="File not found in deterministic file store.",
                metadata=request.metadata,
            )

        content = self._files[absolute_path]
        preview = content[: request.preview_length] if request.preview_length > 0 else ""
        digest = sha256(content.encode("utf-8")).hexdigest()
        return FileReadResult(
            request_id=request.request_id,
            path=absolute_path,
            success=True,
            content=content,
            preview=preview,
            digest=digest,
            metadata=request.metadata,
        )

    def _validate_path(
        self,
        request_id: str,
        workspace_root: Path,
        requested_path: Path | str,
    ) -> FileReadResult | None:
        if not isinstance(requested_path, (Path, str)):
            return FileReadResult(
                request_id=request_id,
                path=workspace_root,
                success=False,
                error_code=FileReadErrorCode.UNSUPPORTED_INPUT,
                error_message="Requested path must be a pathlib.Path or string value.",
            )
        requested_text = str(requested_path)
        if not requested_text or "\x00" in requested_text:
            return FileReadResult(
                request_id=request_id,
                path=workspace_root,
                success=False,
                error_code=FileReadErrorCode.INVALID_PATH,
                error_message="Requested path is invalid.",
            )
        path_value = Path(requested_text)
        if path_value.is_absolute():
            normalized = path_value.resolve(strict=False)
            try:
                normalized.relative_to(workspace_root)
            except ValueError:
                return FileReadResult(
                    request_id=request_id,
                    path=normalized,
                    success=False,
                    error_code=FileReadErrorCode.PATH_OUTSIDE_WORKSPACE,
                    error_message="Requested path escapes the workspace boundary.",
                )
        return None

    def _normalize_path(self, workspace_root: Path, requested_path: Path) -> Path:
        candidate = requested_path if requested_path.is_absolute() else workspace_root / requested_path
        return candidate.resolve(strict=False)

    def _is_within_workspace(self, workspace_root: Path, candidate: Path) -> bool:
        try:
            candidate.relative_to(workspace_root)
        except ValueError:
            return False
        return True
