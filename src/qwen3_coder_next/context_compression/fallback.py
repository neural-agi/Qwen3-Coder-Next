"""Narrow deterministic fallback for successful retrieval with empty ranking."""
from __future__ import annotations

from dataclasses import dataclass, field

from qwen3_coder_next.context_compression.retriever import RetrievalResult
from qwen3_coder_next.context_compression.schemas import EvidenceChunk
from qwen3_coder_next.context_compression.ranker import RankingResult


@dataclass(frozen=True, slots=True)
class FallbackResult:
    chunks: tuple[EvidenceChunk, ...] = field(default_factory=tuple)
    activated: bool = False
    reason_code: str = ""


class ContextFallback:
    """Select one valid retrieved candidate only for the documented empty-ranking case."""

    def select(self, retrieval: RetrievalResult, ranking: RankingResult) -> FallbackResult:
        if not isinstance(retrieval, RetrievalResult) or not isinstance(ranking, RankingResult):
            raise ValueError("retrieval and ranking must use context contracts.")
        if ranking.chunks or not retrieval.chunks or retrieval.issues:
            return FallbackResult(tuple(ranking.chunks), False, "")
        candidate = min(retrieval.chunks, key=lambda chunk: (chunk.source_id, chunk.location, chunk.excerpt, chunk.provenance))
        return FallbackResult((candidate,), True, "ranking_empty_after_successful_retrieval")
