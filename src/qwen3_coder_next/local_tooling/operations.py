"""Filesystem operation abstractions for the local tooling layer."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

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
