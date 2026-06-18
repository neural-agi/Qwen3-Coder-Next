"""Filesystem service abstractions for the local tooling layer."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class FileSystemOperationRequest:
    """Immutable request for a filesystem service operation."""

    request_id: str
    path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FileSystemOperationResult:
    """Immutable result returned by a filesystem service operation."""

    request_id: str
    path: Path
    exists: bool
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class FileSystemService(ABC):
    """Abstract filesystem service interface for local tooling."""

    @abstractmethod
    def read(self, request: FileSystemOperationRequest) -> FileSystemOperationResult:
        """Read data for the supplied request."""

    @abstractmethod
    def write(
        self,
        request: FileSystemOperationRequest,
        content: str,
    ) -> FileSystemOperationResult:
        """Write data for the supplied request."""

    @abstractmethod
    def exists(self, request: FileSystemOperationRequest) -> FileSystemOperationResult:
        """Check whether the supplied path exists."""


class DeterministicFileSystemService(FileSystemService):
    """Deterministic in-memory filesystem service for foundation testing."""

    def __init__(self, files: dict[Path, str] | None = None) -> None:
        self._files = dict(files or {})

    def read(self, request: FileSystemOperationRequest) -> FileSystemOperationResult:
        """Return the current content for a path without touching disk."""

        content = self._files.get(request.path, "")
        return FileSystemOperationResult(
            request_id=request.request_id,
            path=request.path,
            exists=request.path in self._files,
            content=content,
        )

    def write(
        self,
        request: FileSystemOperationRequest,
        content: str,
    ) -> FileSystemOperationResult:
        """Record content in memory and return the updated result."""

        self._files[request.path] = content
        return FileSystemOperationResult(
            request_id=request.request_id,
            path=request.path,
            exists=True,
            content=content,
        )

    def exists(self, request: FileSystemOperationRequest) -> FileSystemOperationResult:
        """Check whether the supplied path is stored in memory."""

        exists = request.path in self._files
        return FileSystemOperationResult(
            request_id=request.request_id,
            path=request.path,
            exists=exists,
            content=self._files.get(request.path, ""),
        )
