
"""Deterministic memory retrieval and ranking for Part 5 Step 5."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Iterable, Mapping

from qwen3_coder_next.memory.project_store import ProjectMemoryStore
from qwen3_coder_next.memory.schemas import (
    GlobalPattern,
    MemoryItem,
    MemoryQuery,
    MemoryResult,
    MemoryTier,
    ProjectDecision,
    SessionSummary,
)
from qwen3_coder_next.memory.session_store import SessionMemoryStore
from qwen3_coder_next.memory.serialization import MalformedMemorySerializedDataError
from qwen3_coder_next.memory.state import MemoryState


_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")
_TIER_WEIGHT = {
    MemoryTier.WORKING: 4.0,
    MemoryTier.SESSION: 3.0,
    MemoryTier.PROJECT: 2.0,
    MemoryTier.GLOBAL: 1.0,
}
_CONFIDENCE_WEIGHT = {
    "high": 3.0,
    "medium": 2.0,
    "low": 1.0,
    "unknown": 0.0,
}


@dataclass(frozen=True, slots=True)
class _MemoryCandidate:
    item: MemoryItem
    retrieval_source: str
    source_tier: MemoryTier
    source_id: str
    timestamp: datetime
    metadata: dict[str, Any]

    def fingerprint(self) -> str:
        return json.dumps(self.item.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True, slots=True)
class _RankedCandidate:
    candidate: _MemoryCandidate
    score: float
    rationale: str

    def sort_key(self) -> tuple[float, float, float, str, str]:
        return (
            -self.score,
            -self.candidate.timestamp.replace(tzinfo=UTC).timestamp(),
            -_TIER_WEIGHT[self.candidate.source_tier],
            self.candidate.retrieval_source,
            self.candidate.item.memory_id,
        )


class MemoryRetriever:
    """Deterministic tiered memory retrieval and ranking."""

    def retrieve(
        self,
        query: MemoryQuery,
        *,
        working_memory: MemoryState | None = None,
        session_store: SessionMemoryStore | None = None,
        project_store: ProjectMemoryStore | None = None,
        top_k: int | None = None,
    ) -> tuple[MemoryResult, ...]:
        """Retrieve and rank memory results for a structured query."""

        self._ensure_query(query)
        limit = query.top_k if top_k is None else self._ensure_top_k(top_k)
        candidates = self._collect_candidates(
            query,
            working_memory=working_memory,
            session_store=session_store,
            project_store=project_store,
        )
        ranked = self._rank_candidates(query, candidates)
        selected: list[MemoryResult] = []
        seen: set[str] = set()
        for ranked_candidate in ranked:
            fingerprint = ranked_candidate.candidate.fingerprint()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            selected.append(
                MemoryResult(
                    item=ranked_candidate.candidate.item,
                    score=ranked_candidate.score,
                    rationale=ranked_candidate.rationale,
                    retrieval_source=ranked_candidate.candidate.retrieval_source,
                )
            )
            if len(selected) >= limit:
                break
        return tuple(selected)

    def _collect_candidates(
        self,
        query: MemoryQuery,
        *,
        working_memory: MemoryState | None,
        session_store: SessionMemoryStore | None,
        project_store: ProjectMemoryStore | None,
    ) -> tuple[_MemoryCandidate, ...]:
        candidates: list[_MemoryCandidate] = []
        if working_memory is not None:
            candidates.extend(self._collect_state_candidates(working_memory, source_kind="working"))
        if session_store is not None:
            for state in session_store.list_session_states():
                if query.session_id is not None and state.state_id != query.session_id:
                    continue
                candidates.extend(self._collect_state_candidates(state, source_kind="session"))
        if project_store is not None:
            for state in project_store.list_project_states():
                if query.project_id is not None and state.state_id != query.project_id:
                    continue
                candidates.extend(self._collect_state_candidates(state, source_kind="project"))
        return tuple(candidates)

    def _collect_state_candidates(self, state: MemoryState, *, source_kind: str) -> list[_MemoryCandidate]:
        candidates: list[_MemoryCandidate] = []
        state_timestamp = state.updated_at
        for item in state.memory_items:
            candidates.append(
                self._candidate_from_item(
                    item,
                    retrieval_source=f"{source_kind}-store:{state.state_id}",
                    source_tier=item.tier,
                    source_id=state.state_id,
                    timestamp=item.timestamp,
                    metadata={"state_id": state.state_id, "source_kind": source_kind},
                )
            )
        for index, summary in enumerate(state.session_summaries, start=1):
            candidates.append(self._candidate_from_session_summary(state, summary, index, source_kind, state_timestamp))
        for decision in state.project_decisions:
            candidates.append(self._candidate_from_project_decision(state, decision, source_kind, state_timestamp))
        for index, pattern in enumerate(state.global_patterns, start=1):
            candidates.append(self._candidate_from_global_pattern(state, pattern, index, source_kind, state_timestamp))
        return candidates

    def _candidate_from_item(
        self,
        item: MemoryItem,
        *,
        retrieval_source: str,
        source_tier: MemoryTier,
        source_id: str,
        timestamp: datetime,
        metadata: Mapping[str, Any],
    ) -> _MemoryCandidate:
        return _MemoryCandidate(
            item=item,
            retrieval_source=retrieval_source,
            source_tier=source_tier,
            source_id=source_id,
            timestamp=timestamp,
            metadata=dict(metadata),
        )

    def _candidate_from_session_summary(
        self,
        state: MemoryState,
        summary: SessionSummary,
        index: int,
        source_kind: str,
        timestamp: datetime,
    ) -> _MemoryCandidate:
        item = MemoryItem(
            memory_id=f"{state.state_id}-session-summary-{index:04d}",
            tier=MemoryTier.SESSION,
            subject=f"Session summary {index:04d}",
            content=self._compose_session_summary_content(summary),
            source=f"{source_kind}-store:{state.state_id}",
            timestamp=timestamp,
            confidence="medium",
            tags=("session-summary",),
            references=(summary.session_id, state.state_id),
        )
        return self._candidate_from_item(
            item,
            retrieval_source=f"{source_kind}-store:{state.state_id}#summary-{index:04d}",
            source_tier=MemoryTier.SESSION,
            source_id=state.state_id,
            timestamp=timestamp,
            metadata={"state_id": state.state_id, "source_kind": source_kind, "summary_index": index},
        )

    def _candidate_from_project_decision(
        self,
        state: MemoryState,
        decision: ProjectDecision,
        source_kind: str,
        timestamp: datetime,
    ) -> _MemoryCandidate:
        item = MemoryItem(
            memory_id=f"{decision.project_id}-decision-v{decision.version:04d}",
            tier=MemoryTier.PROJECT,
            subject=decision.decision,
            content=self._compose_project_decision_content(decision),
            source=f"{source_kind}-store:{state.state_id}",
            timestamp=timestamp,
            confidence="high",
            tags=("project-decision",),
            references=(decision.project_id, f"version:{decision.version}"),
        )
        return self._candidate_from_item(
            item,
            retrieval_source=f"{source_kind}-store:{state.state_id}#decision-v{decision.version:04d}",
            source_tier=MemoryTier.PROJECT,
            source_id=state.state_id,
            timestamp=timestamp,
            metadata={"state_id": state.state_id, "source_kind": source_kind, "decision_version": decision.version},
        )

    def _candidate_from_global_pattern(
        self,
        state: MemoryState,
        pattern: GlobalPattern,
        index: int,
        source_kind: str,
        timestamp: datetime,
    ) -> _MemoryCandidate:
        slug = self._slugify(pattern.pattern_name)
        item = MemoryItem(
            memory_id=f"global-pattern-{index:04d}-{slug}",
            tier=MemoryTier.GLOBAL,
            subject=pattern.pattern_name,
            content=self._compose_global_pattern_content(pattern),
            source=f"{source_kind}-store:{state.state_id}",
            timestamp=timestamp,
            confidence="medium",
            tags=("global-pattern",),
            references=(pattern.pattern_name, state.state_id),
        )
        return self._candidate_from_item(
            item,
            retrieval_source=f"{source_kind}-store:{state.state_id}#global-pattern-{index:04d}",
            source_tier=MemoryTier.GLOBAL,
            source_id=state.state_id,
            timestamp=timestamp,
            metadata={"state_id": state.state_id, "source_kind": source_kind, "pattern_index": index},
        )

    def _rank_candidates(self, query: MemoryQuery, candidates: Iterable[_MemoryCandidate]) -> tuple[_RankedCandidate, ...]:
        ranked = [self._rank_candidate(query, candidate) for candidate in candidates]
        ranked.sort(key=_RankedCandidate.sort_key)
        deduplicated: list[_RankedCandidate] = []
        seen: set[str] = set()
        for ranked_candidate in ranked:
            fingerprint = ranked_candidate.candidate.fingerprint()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            deduplicated.append(ranked_candidate)
        return tuple(deduplicated)

    def _rank_candidate(self, query: MemoryQuery, candidate: _MemoryCandidate) -> _RankedCandidate:
        relevance = self._query_relevance(query.query_text, candidate)
        tier_bonus = self._tier_bonus(query, candidate)
        confidence = _CONFIDENCE_WEIGHT.get(candidate.item.confidence.lower(), 0.0)
        freshness = self._freshness_score(candidate.timestamp)
        filter_bonus = self._filter_bonus(query.filters, candidate)
        score = relevance + tier_bonus + confidence + freshness + filter_bonus
        rationale = self._build_rationale(query, candidate, relevance, tier_bonus, confidence, freshness, filter_bonus)
        return _RankedCandidate(candidate=candidate, score=score, rationale=rationale)

    def _query_relevance(self, query_text: str, candidate: _MemoryCandidate) -> float:
        query_tokens = self._tokenize(query_text)
        if not query_tokens:
            return 0.0
        candidate_tokens = self._tokenize(
            " ".join(
                [
                    candidate.item.subject,
                    candidate.item.content,
                    candidate.item.source,
                    " ".join(candidate.item.tags),
                    " ".join(candidate.item.references),
                ]
            )
        )
        overlap = len(query_tokens & candidate_tokens)
        relevance = overlap / len(query_tokens)
        if query_text.lower() in candidate.item.content.lower():
            relevance += 0.5
        return relevance * 100.0

    def _tier_bonus(self, query: MemoryQuery, candidate: _MemoryCandidate) -> float:
        if query.tier_hint is None:
            return _TIER_WEIGHT[candidate.source_tier]
        if candidate.item.tier == query.tier_hint:
            return _TIER_WEIGHT[candidate.source_tier] + 10.0
        return _TIER_WEIGHT[candidate.source_tier]

    def _filter_bonus(self, filters: Mapping[str, Any], candidate: _MemoryCandidate) -> float:
        if not filters:
            return 0.0
        bonus = 0.0
        candidate_map = {
            "memory_id": candidate.item.memory_id,
            "tier": candidate.item.tier.value,
            "subject": candidate.item.subject,
            "content": candidate.item.content,
            "source": candidate.item.source,
            "timestamp": candidate.item.timestamp.isoformat(),
            "confidence": candidate.item.confidence,
            "tags": candidate.item.tags,
            "references": candidate.item.references,
            **candidate.metadata,
        }
        for key, expected in filters.items():
            actual = candidate_map.get(str(key))
            if self._matches_filter(actual, expected):
                bonus += 5.0
        return bonus

    def _matches_filter(self, actual: object, expected: object) -> bool:
        if isinstance(expected, (tuple, list, set, frozenset)):
            expected_values = {str(item) for item in expected}
            if isinstance(actual, tuple):
                return expected_values.issubset({str(item) for item in actual})
            return str(actual) in expected_values
        if actual is None:
            return False
        return str(actual) == str(expected)

    def _freshness_score(self, timestamp: datetime) -> float:
        return max(timestamp.replace(tzinfo=UTC).timestamp(), 0.0) / 1_000_000.0

    def _build_rationale(
        self,
        query: MemoryQuery,
        candidate: _MemoryCandidate,
        relevance: float,
        tier_bonus: float,
        confidence: float,
        freshness: float,
        filter_bonus: float,
    ) -> str:
        reasons: list[str] = []
        if relevance:
            reasons.append(f"relevance={relevance:.3f}")
        if query.tier_hint is not None:
            reasons.append(f"tier_hint={query.tier_hint.value}")
        if tier_bonus:
            reasons.append(f"tier_bonus={tier_bonus:.3f}")
        if confidence:
            reasons.append(f"confidence={confidence:.3f}")
        if freshness:
            reasons.append(f"freshness={freshness:.6f}")
        if filter_bonus:
            reasons.append(f"filters={filter_bonus:.3f}")
        reasons.append(f"source={candidate.retrieval_source}")
        return "; ".join(reasons)

    @staticmethod
    def _compose_session_summary_content(summary: SessionSummary) -> str:
        return " | ".join(
            [
                f"goal={summary.goal}",
                f"outcomes={' ; '.join(summary.outcomes) if summary.outcomes else 'none'}",
                f"decisions={' ; '.join(summary.decisions) if summary.decisions else 'none'}",
                f"open_questions={' ; '.join(summary.open_questions) if summary.open_questions else 'none'}",
            ]
        )

    @staticmethod
    def _compose_project_decision_content(decision: ProjectDecision) -> str:
        return " | ".join(
            [
                f"decision={decision.decision}",
                f"rationale={decision.rationale}",
                f"alternatives={' ; '.join(decision.alternatives) if decision.alternatives else 'none'}",
                f"version={decision.version}",
            ]
        )

    @staticmethod
    def _compose_global_pattern_content(pattern: GlobalPattern) -> str:
        return " | ".join(
            [
                f"applicability={pattern.applicability}",
                f"evidence={' ; '.join(pattern.evidence) if pattern.evidence else 'none'}",
                f"caveats={' ; '.join(pattern.caveats) if pattern.caveats else 'none'}",
            ]
        )

    @staticmethod
    def _tokenize(value: str) -> set[str]:
        return {token.lower() for token in _TOKEN_PATTERN.findall(value or "")}

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "pattern"

    @staticmethod
    def _ensure_query(query: object) -> None:
        if not isinstance(query, MemoryQuery):
            raise ValueError("query must be a MemoryQuery instance.")

    @staticmethod
    def _ensure_top_k(top_k: object) -> int:
        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError("top_k must be a positive integer.")
        return top_k


def retrieve_memory(
    query: MemoryQuery,
    *,
    working_memory: MemoryState | None = None,
    session_store: SessionMemoryStore | None = None,
    project_store: ProjectMemoryStore | None = None,
    top_k: int | None = None,
) -> tuple[MemoryResult, ...]:
    """Convenience wrapper around MemoryRetriever."""

    return MemoryRetriever().retrieve(
        query,
        working_memory=working_memory,
        session_store=session_store,
        project_store=project_store,
        top_k=top_k,
    )
