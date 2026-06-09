"""Memory contracts shared across the codebase."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MemoryKind(StrEnum):
    """Supported memory categories."""

    EPISODIC = "episodic"
    WORKING = "working"
    FACT = "fact"


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """Immutable memory record."""

    memory_id: str
    kind: MemoryKind
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
