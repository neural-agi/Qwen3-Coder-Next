"""Small deterministic benchmark helpers for evaluation acceptance cases."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from qwen3_coder_next.evaluation.coordinator import EvaluationCoordinator
from qwen3_coder_next.evaluation.schemas import EvaluationRunRequest


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    """A labeled evaluation case with caller-supplied deterministic latency."""

    request: EvaluationRunRequest
    expected_decision: str
    latency_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Aggregate benchmark metrics without imposing a performance threshold."""

    case_count: int
    approval_rate: float
    false_approval_rate: float
    average_latency_ms: float


def run_benchmark(cases: Iterable[BenchmarkCase]) -> BenchmarkResult:
    """Evaluate labeled cases deterministically and report aggregate metrics."""

    materialized = tuple(cases)
    if any(not isinstance(case, BenchmarkCase) or case.latency_ms < 0 for case in materialized):
        raise ValueError("cases must contain valid BenchmarkCase values.")
    decisions = tuple(EvaluationCoordinator().evaluate(case.request)[0].decision for case in materialized)
    approvals = sum(decision == "approve" for decision in decisions)
    false_approvals = sum(decision == "approve" and decision != case.expected_decision for decision, case in zip(decisions, materialized))
    latency = sum(case.latency_ms for case in materialized)
    count = len(materialized)
    return BenchmarkResult(count, approvals / count if count else 0.0, false_approvals / count if count else 0.0, latency / count if count else 0.0)
