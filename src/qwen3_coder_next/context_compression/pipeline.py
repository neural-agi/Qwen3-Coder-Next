"""Deterministic Context Compression pipeline for Part 11 Step 8."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from qwen3_coder_next.context_compression.budget import BudgetManager
from qwen3_coder_next.context_compression.cache import ContextPackageCache
from qwen3_coder_next.context_compression.fallback import ContextFallback
from qwen3_coder_next.context_compression.packager import ContextPackager, context_cache_key
from qwen3_coder_next.context_compression.ranker import EvidenceDeduplicator, EvidenceRanker, RankingResult
from qwen3_coder_next.context_compression.request_normalizer import ContextRequestNormalizer
from qwen3_coder_next.context_compression.retriever import ContextRetriever
from qwen3_coder_next.context_compression.schemas import CompressionConfig, ContextPackage
from qwen3_coder_next.context_compression.source_resolver import SourcePlan, SourceResolver, SourceSpec
from qwen3_coder_next.context_compression.summarizer import EvidenceSummarizer
from qwen3_coder_next.context_compression.telemetry import CompressionTelemetry


@dataclass(frozen=True, slots=True)
class ContextPipelineResult:
    status: str
    package: ContextPackage | None = None
    cache_status: str = "miss"
    fallback_activated: bool = False
    failure_reason: str = ""
    telemetry: tuple[dict[str, object], ...] = ()


class ContextCompressionPipeline:
    def __init__(self, retriever: ContextRetriever, *, normalizer=None, resolver=None, ranker=None, deduplicator=None, summarizer=None, budget_manager=None, packager=None, fallback=None, cache=None, telemetry=None):
        if not isinstance(retriever, ContextRetriever):
            raise ValueError("retriever must be a ContextRetriever.")
        self._retriever = retriever
        self._normalizer = normalizer or ContextRequestNormalizer()
        self._resolver = resolver or SourceResolver()
        self._ranker = ranker or EvidenceRanker()
        self._deduplicator = deduplicator or EvidenceDeduplicator()
        self._summarizer = summarizer or EvidenceSummarizer()
        self._budget = budget_manager or BudgetManager()
        self._packager = packager or ContextPackager()
        self._fallback = fallback or ContextFallback()
        self._cache = cache or ContextPackageCache()
        self._telemetry = telemetry or CompressionTelemetry()

    def run(self, raw_request: object, sources: Iterable[SourceSpec], config: CompressionConfig, reserved_budget: int = 0, *, policy_version: str = "extractive-default-v1") -> ContextPipelineResult:
        request = self._normalizer.normalize(raw_request)
        plan = self._resolver.resolve(request, sources)
        retrieval = self._retriever.retrieve(request, plan)
        self._emit("retrieval", candidates=len(retrieval.chunks), issues=len(retrieval.issues))
        if retrieval.issues:
            self._emit("failure", reason="retrieval_issues", issues=len(retrieval.issues))
            return self._result("failure", failure_reason="retrieval_issues")
        key = context_cache_key(request, plan, config, policy_version, reserved_budget, retrieval.chunks)
        cached = self._cache.get(key, config)
        self._emit("cache", status=cached.status)
        if cached.status == "hit":
            return self._result("cache_hit", cached.package, cache_status="hit")
        ranking = self._ranker.rank(request, retrieval.chunks, plan)
        deduped = self._deduplicator.deduplicate(ranking.chunks, config)
        self._emit("ranking", candidates=len(ranking.chunks), deduplicated=len(deduped.chunks))
        if deduped.chunks:
            candidates = deduped.chunks
            fallback_activated = False
        else:
            fallback = self._fallback.select(retrieval, RankingResult())
            candidates = fallback.chunks
            fallback_activated = fallback.activated
            self._emit("fallback", activated=fallback.activated, reason=fallback.reason_code or "none", candidates=len(candidates))
        if not candidates:
            self._emit("failure", reason="no_valid_ranked_evidence")
            return self._result("failure", failure_reason="no_valid_ranked_evidence", fallback_activated=fallback_activated)
        summary = self._summarizer.summarize(request, candidates, config)
        self._emit("summary", claims=len(summary.claims), omissions=len(summary.omissions), budget_exceeded=summary.budget_exceeded)
        budget = self._budget.apply(request, summary, request.token_budget, reserved_budget, config)
        self._emit("budget", used=budget.report.used_budget, dropped=len(budget.report.dropped_sources), feasible=budget.feasible)
        if not budget.feasible:
            self._emit("failure", reason="budget_infeasible", dropped=len(budget.report.dropped_sources))
            return self._result("infeasible", failure_reason="budget_infeasible", fallback_activated=fallback_activated)
        package = self._packager.package(request, summary, budget, candidates, plan, config)
        self._cache.put(key, package, budget.report, config)
        self._emit("package", selected=len(package.selected_chunks), provenance=len(package.provenance_map))
        return self._result("success", package, fallback_activated=fallback_activated)

    def _emit(self, event_type: str, **fields: object) -> None:
        self._telemetry.record(event_type, fields)

    def _result(self, status: str, package=None, *, cache_status="miss", fallback_activated=False, failure_reason="") -> ContextPipelineResult:
        return ContextPipelineResult(status, package, cache_status, fallback_activated, failure_reason, tuple(event.to_dict() for event in self._telemetry.events))
