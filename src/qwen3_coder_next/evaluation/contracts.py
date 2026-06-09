"""Evaluation contracts shared across the codebase."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EvaluationStatus(StrEnum):
    """Supported evaluation lifecycle states."""

    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True, slots=True)
class EvaluationScore:
    """Immutable score produced by an evaluation."""

    value: float
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvaluationRequest:
    """Immutable request sent to an evaluator."""

    request_id: str
    target: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvaluationOutcome:
    """Immutable outcome returned by an evaluator."""

    request_id: str
    status: EvaluationStatus
    score: EvaluationScore
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Alias-style wrapper for a completed evaluation result."""

    outcome: EvaluationOutcome
