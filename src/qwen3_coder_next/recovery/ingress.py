"""Failure ingress normalization without diagnosis or recovery decisions."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from qwen3_coder_next.recovery.contracts import FailureEvent, Severity


class FailureIngress:
    """Convert supported raw failure envelopes into immutable FailureEvent values."""

    _SUPPORTED_SOURCES = frozenset({"agent", "tool", "orchestrator", "testing", "review", "deployment"})

    def normalize(self, raw: BaseException | Mapping[str, Any], *, task_id: str, source_agent: str, timestamp: str) -> FailureEvent:
        if not task_id or not isinstance(task_id, str):
            raise ValueError("task_id must be non-empty text.")
        if source_agent not in self._SUPPORTED_SOURCES:
            raise ValueError("source_agent is unsupported.")
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError("timestamp must be non-empty text.")
        if isinstance(raw, BaseException):
            return FailureEvent(task_id, source_agent, type(raw).__name__.lower(), Severity.HIGH, str(raw) or type(raw).__name__, timestamp, raw_payload=repr(raw))
        if not isinstance(raw, Mapping):
            raise ValueError("raw failure must be an exception or mapping.")
        required = ("failure_type", "message", "severity")
        if any(key not in raw for key in required):
            raise ValueError("raw failure envelope is missing required fields.")
        try:
            severity = Severity(raw["severity"])
        except (TypeError, ValueError) as exc:
            raise ValueError("severity is invalid.") from exc
        retry_count = raw.get("retry_count", 0)
        return FailureEvent(task_id, source_agent, raw["failure_type"], severity, raw["message"], timestamp, stack_trace_ref=raw.get("stack_trace_ref", ""), tool_ref=raw.get("tool_ref", ""), retry_count=retry_count, worktree_ref=raw.get("worktree_ref", ""), raw_payload=raw.get("raw_payload", ""))
