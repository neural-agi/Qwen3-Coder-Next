"""Prompt contracts shared across the prompt infrastructure."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PromptFormat(StrEnum):
    """Supported prompt template formats."""

    TEXT = "text"


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    """Immutable prompt template with version metadata."""

    name: str
    version: str
    content: str
    description: str = ""
    format: PromptFormat = PromptFormat.TEXT
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PromptLoadRequest:
    """Request describing a prompt to load from storage."""

    name: str
    version: str


@dataclass(frozen=True, slots=True)
class PromptLoadResult:
    """Result returned by a prompt loader."""

    template: PromptTemplate
    source_path: str
