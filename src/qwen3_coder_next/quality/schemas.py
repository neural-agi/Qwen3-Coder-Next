"""Stable Part 6 quality contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")
    return value


def _tuple_text(value: object, name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raise ValueError(f"{name} must not be a string.")
    result = tuple(value)  # type: ignore[arg-type]
    if any(not isinstance(item, str) or not item.strip() for item in result):
        raise ValueError(f"{name} must contain non-empty strings.")
    return result


@dataclass(frozen=True, slots=True)
class TestInvocation:
    task_id: str
    worktree_id: str
    runner: str
    command: tuple[str, ...]
    timeout: int
    cwd: str
    env_profile: str

    def __post_init__(self) -> None:
        for name in ("task_id", "worktree_id", "runner", "cwd", "env_profile"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "command", _tuple_text(self.command, "command"))
        if not isinstance(self.timeout, int) or self.timeout <= 0:
            raise ValueError("timeout must be a positive integer.")

    def to_dict(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "worktree_id": self.worktree_id, "runner": self.runner,
                "command": list(self.command), "timeout": self.timeout, "cwd": self.cwd,
                "env_profile": self.env_profile}


@dataclass(frozen=True, slots=True)
class TestReport:
    task_id: str
    worktree_id: str
    suite_name: str
    exit_code: int
    status: str
    summary: str
    failed_cases: tuple[str, ...] = ()
    logs_ref: str = ""
    artifacts_ref: str = ""

    def __post_init__(self) -> None:
        for name in ("task_id", "worktree_id", "suite_name", "status", "summary"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if not isinstance(self.exit_code, int):
            raise ValueError("exit_code must be an integer.")
        object.__setattr__(self, "failed_cases", _tuple_text(self.failed_cases, "failed_cases"))

    def to_dict(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "worktree_id": self.worktree_id, "suite_name": self.suite_name,
                "exit_code": self.exit_code, "status": self.status, "summary": self.summary,
                "failed_cases": list(self.failed_cases), "logs_ref": self.logs_ref,
                "artifacts_ref": self.artifacts_ref}


@dataclass(frozen=True, slots=True)
class ReviewInstruction:
    task_id: str
    diff_ref: str
    rubric_id: str
    context_budget: int
    policy_profile: str

    def __post_init__(self) -> None:
        for name in ("task_id", "diff_ref", "rubric_id", "policy_profile"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if not isinstance(self.context_budget, int) or self.context_budget <= 0:
            raise ValueError("context_budget must be a positive integer.")


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    id: str
    severity: str
    category: str
    summary: str
    evidence_ref: str
    recommendation: str

    def __post_init__(self) -> None:
        for name in ("id", "severity", "category", "summary", "evidence_ref", "recommendation"):
            object.__setattr__(self, name, _text(getattr(self, name), name))

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in ("id", "severity", "category", "summary", "evidence_ref", "recommendation")}


@dataclass(frozen=True, slots=True)
class ReviewReport:
    task_id: str
    worktree_id: str
    score: float
    findings: tuple[ReviewFinding, ...] = ()
    overall_status: str = "pass"
    reviewer_notes: str = ""
    artifacts_ref: str = ""

    def __post_init__(self) -> None:
        for name in ("task_id", "worktree_id", "overall_status"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if not isinstance(self.score, (int, float)) or not 0 <= self.score <= 1:
            raise ValueError("score must be between 0 and 1.")
        if isinstance(self.findings, (str, bytes)):
            raise ValueError("findings must be a collection.")
        object.__setattr__(self, "findings", tuple(self.findings))

    def to_dict(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "worktree_id": self.worktree_id, "score": self.score,
                "findings": [item.to_dict() for item in self.findings], "overall_status": self.overall_status,
                "reviewer_notes": self.reviewer_notes, "artifacts_ref": self.artifacts_ref}


@dataclass(frozen=True, slots=True)
class GateDecision:
    task_id: str
    decision: str
    reasons: tuple[str, ...] = ()
    blocking_findings: tuple[str, ...] = ()
    retryable_findings: tuple[str, ...] = ()
    next_action: str = "proceed"

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_id", _text(self.task_id, "task_id"))
        object.__setattr__(self, "decision", _text(self.decision, "decision"))
        for name in ("reasons", "blocking_findings", "retryable_findings"):
            object.__setattr__(self, name, _tuple_text(getattr(self, name), name))


@dataclass(frozen=True, slots=True)
class FeedbackBundle:
    task_id: str
    user_visible_summary: str
    machine_actionable_notes: tuple[str, ...] = ()
    rerun_hints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_id", _text(self.task_id, "task_id"))
        object.__setattr__(self, "user_visible_summary", _text(self.user_visible_summary, "user_visible_summary"))
        object.__setattr__(self, "machine_actionable_notes", _tuple_text(self.machine_actionable_notes, "machine_actionable_notes"))
        object.__setattr__(self, "rerun_hints", _tuple_text(self.rerun_hints, "rerun_hints"))
