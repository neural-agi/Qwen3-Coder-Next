"""Diff generation abstractions for the local tooling layer."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from difflib import unified_diff


@dataclass(frozen=True, slots=True)
class DiffRequest:
    """Immutable request for generating a file diff."""

    request_id: str
    path: Path
    before: str
    after: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DiffResult:
    """Immutable result returned by a diff service."""

    request_id: str
    path: Path
    has_changes: bool
    diff_text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class DiffService(ABC):
    """Abstract diff generation interface."""

    @abstractmethod
    def generate_diff(self, request: DiffRequest) -> DiffResult:
        """Generate a deterministic diff for the supplied request."""


class DeterministicDiffService(DiffService):
    """Deterministic diff service using unified diff output."""

    def generate_diff(self, request: DiffRequest) -> DiffResult:
        """Return a unified diff for the before/after text snapshots."""

        before_lines = request.before.splitlines(keepends=True)
        after_lines = request.after.splitlines(keepends=True)
        diff_lines = list(
            unified_diff(
                before_lines,
                after_lines,
                fromfile=f"{request.path.as_posix()} (before)",
                tofile=f"{request.path.as_posix()} (after)",
                lineterm="",
            )
        )
        diff_text = "\n".join(diff_lines)
        return DiffResult(
            request_id=request.request_id,
            path=request.path,
            has_changes=request.before != request.after,
            diff_text=diff_text,
            metadata=request.metadata,
        )
