"""Deterministic evidence ranking and exact deduplication for Part 11 Step 4."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from math import isfinite

from qwen3_coder_next.context_compression.schemas import CompressionConfig, ContextRequest, EvidenceChunk
from qwen3_coder_next.context_compression.source_resolver import SourcePlan


_SCORE_WEIGHT = 0.4
_RECENCY_WEIGHT = 0.2
_SOURCE_PRIORITY_WEIGHT = 0.2
_INTENT_MATCH_WEIGHT = 0.2
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")


def _validate_chunks(chunks: object) -> tuple[EvidenceChunk, ...]:
    if isinstance(chunks, (str, bytes)):
        raise ValueError("chunks must be a collection of EvidenceChunk values.")
    try:
        values = tuple(chunks or ())  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValueError("chunks must be a collection of EvidenceChunk values.") from exc
    if any(not isinstance(item, EvidenceChunk) for item in values):
        raise ValueError("chunks contains an invalid EvidenceChunk.")
    for item in values:
        if not all(isfinite(value) for value in (item.score, item.recency)):
            raise ValueError("evidence scores must be finite.")
    return values


@dataclass(frozen=True, slots=True)
class RankingResult:
    chunks: tuple[EvidenceChunk, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "chunks", tuple(self.chunks))


@dataclass(frozen=True, slots=True)
class DeduplicationResult:
    chunks: tuple[EvidenceChunk, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "chunks", tuple(self.chunks))


class EvidenceRanker:
    """Rank evidence using only fields available in the frozen contracts."""

    def rank(self, request: ContextRequest, chunks: object, plan: SourcePlan) -> RankingResult:
        if not isinstance(request, ContextRequest):
            raise ValueError("request must be a ContextRequest.")
        if not isinstance(plan, SourcePlan):
            raise ValueError("plan must be a SourcePlan.")
        values = _validate_chunks(chunks)
        priorities = {entry.source_id: entry.priority for entry in plan.entries}
        scored: list[tuple[float, EvidenceChunk]] = []
        for chunk in values:
            priority = priorities.get(chunk.source_id, 0.0)
            match = self._intent_match(request.intent, chunk)
            score = (_SCORE_WEIGHT * chunk.score) + (_RECENCY_WEIGHT * chunk.recency) + (_SOURCE_PRIORITY_WEIGHT * priority) + (_INTENT_MATCH_WEIGHT * match)
            if not isfinite(score):
                raise ValueError("calculated evidence score is not finite.")
            scored.append((score, EvidenceChunk(chunk.source_id, chunk.location, chunk.excerpt, score, chunk.recency, chunk.provenance, chunk.schema_version, chunk.retrieval_timestamp, chunk.confidence)))
        scored.sort(key=lambda item: (-item[0], item[1].source_id, item[1].location, item[1].excerpt, item[1].provenance))
        return RankingResult(tuple(chunk for _, chunk in scored))

    @staticmethod
    def _intent_match(intent: str, chunk: EvidenceChunk) -> float:
        intent_tokens = set(_TOKEN_PATTERN.findall(intent.lower()))
        evidence_tokens = set(_TOKEN_PATTERN.findall(f"{chunk.location} {chunk.excerpt}".lower()))
        return len(intent_tokens & evidence_tokens) / len(intent_tokens) if intent_tokens else 0.0


class EvidenceDeduplicator:
    """Merge exact evidence duplicates while retaining all provenance."""

    def deduplicate(self, chunks: object, config: CompressionConfig) -> DeduplicationResult:
        if not isinstance(config, CompressionConfig):
            raise ValueError("config must be a CompressionConfig.")
        values = _validate_chunks(chunks)
        merged: dict[tuple[str, str], EvidenceChunk] = {}
        for chunk in values:
            key = (chunk.location, chunk.excerpt)
            origin = f"source:{chunk.source_id}"
            provenance = tuple(sorted(set((*chunk.provenance, origin))))
            current = merged.get(key)
            if current is None:
                merged[key] = EvidenceChunk(chunk.source_id, chunk.location, chunk.excerpt, chunk.score, chunk.recency, provenance, chunk.schema_version, chunk.retrieval_timestamp, chunk.confidence)
                continue
            merged[key] = EvidenceChunk(
                min(current.source_id, chunk.source_id),
                chunk.location,
                chunk.excerpt,
                max(current.score, chunk.score),
                max(current.recency, chunk.recency),
                tuple(sorted(set((*current.provenance, *chunk.provenance, origin)))),
                max(current.schema_version, chunk.schema_version),
                current.retrieval_timestamp or chunk.retrieval_timestamp,
                current.confidence if current.confidence is not None else chunk.confidence,
            )
        return DeduplicationResult(tuple(sorted(merged.values(), key=lambda item: (item.source_id, item.location, item.excerpt))))
