"""Deterministic strategy registry and retry-budget policy."""
from __future__ import annotations

from dataclasses import dataclass

from qwen3_coder_next.recovery.contracts import (
    DiagnosisReport,
    FailureCategory,
    FailureEvent,
    RecoveryPlan,
    RecoveryStrategy,
)


@dataclass(frozen=True, slots=True)
class StrategyRule:
    """Bounded policy data for one diagnosis category."""

    strategy: RecoveryStrategy
    max_attempts: int
    reason: str
    context_delta: str = ""
    backoff_seconds: int = 0
    preserve_worktree: bool = True

    def __post_init__(self) -> None:
        if self.max_attempts < 0 or self.backoff_seconds < 0:
            raise ValueError("strategy limits must be non-negative.")


_DEFAULT_RULES: dict[FailureCategory, StrategyRule] = {
    FailureCategory.TRANSIENT: StrategyRule(RecoveryStrategy.RETRY_WITH_CONTEXT, 2, "transient failure may be retried with bounded context", "attach the latest failure evidence"),
    FailureCategory.SEMANTIC: StrategyRule(RecoveryStrategy.ALTERNATIVE_APPROACH, 1, "semantic failure requires a different approach"),
    FailureCategory.ENVIRONMENTAL: StrategyRule(RecoveryStrategy.RETRY_WITH_CONTEXT, 1, "environmental failure may be retried after context refresh", "refresh environment context"),
    FailureCategory.UNRECOVERABLE: StrategyRule(RecoveryStrategy.ABORT, 0, "unrecoverable failure cannot be retried"),
    FailureCategory.UNKNOWN: StrategyRule(RecoveryStrategy.ESCALATE, 0, "unknown failure requires explicit human review"),
}


class StrategyRegistry:
    """Select a bounded recovery plan without executing it."""

    def __init__(self, rules: dict[FailureCategory, StrategyRule] | None = None) -> None:
        selected = _DEFAULT_RULES if rules is None else rules
        if not isinstance(selected, dict):
            raise ValueError("rules must be a mapping.")
        if any(not isinstance(category, FailureCategory) or not isinstance(rule, StrategyRule) for category, rule in selected.items()):
            raise ValueError("rules contain invalid entries.")
        self._rules = dict(selected)

    def select(self, diagnosis: DiagnosisReport, event: FailureEvent) -> RecoveryPlan:
        if not isinstance(diagnosis, DiagnosisReport) or not isinstance(event, FailureEvent):
            raise ValueError("diagnosis and event are required.")
        rule = self._rules.get(diagnosis.category)
        if rule is None:
            raise ValueError("diagnosis category is unsupported by this registry.")
        if event.retry_count >= rule.max_attempts:
            strategy = RecoveryStrategy.ESCALATE if diagnosis.category is not FailureCategory.UNRECOVERABLE else RecoveryStrategy.ABORT
        else:
            strategy = rule.strategy
        attempts = max(0, rule.max_attempts - event.retry_count)
        return RecoveryPlan(strategy, rule.reason, rule.context_delta, rule.backoff_seconds, rule.preserve_worktree, attempts)
