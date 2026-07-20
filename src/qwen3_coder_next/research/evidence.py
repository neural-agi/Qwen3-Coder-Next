"""Deterministic evidence normalization and ranking for Part 4 Step 5."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Iterable, Mapping
from uuid import NAMESPACE_URL, uuid5

from qwen3_coder_next.research.fetchers import ResearchFetchResult
from qwen3_coder_next.research.scanner import RepositoryScanResult
from qwen3_coder_next.research.schemas import (
    RESEARCH_SCHEMA_VERSION,
    EvidenceFreshness,
    EvidenceItem,
    EvidenceProvenance,
    ResearchRequest,
    SourcePolicy,
    SourceType,
)


class ResearchEvidenceNormalizationError(ValueError):
    """Base error for evidence normalization failures."""


class MalformedResearchEvidenceError(ResearchEvidenceNormalizationError):
    """Raised when raw evidence cannot be normalized."""


_REQUEST_MATCH_WEIGHT = 0.4
_FRESHNESS_WEIGHT = 0.2
_RELEVANCE_WEIGHT = 0.3
_CONFIDENCE_WEIGHT = 0.2


@dataclass(frozen=True, slots=True, order=True)
class _RankingKey:
    """Immutable internal ranking key for deterministic ordering."""

    source_score: float
    request_match_score: float
    freshness_score: float
    relevance_confidence_score: float
    precision_score: int
    source_ref: str
    evidence_id: str


@dataclass(frozen=True, slots=True)
class ResearchEvidenceNormalizationResult:
    """Structured output returned by the evidence normalizer."""

    evidence_items: tuple[EvidenceItem, ...]
    normalized_at: datetime = field(default_factory=lambda: datetime.fromtimestamp(0, UTC))
    schema_version: int = RESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the normalization result into a deterministic mapping."""

        return {
            "evidence_items": [item.to_dict() for item in self.evidence_items],
            "normalized_at": self.normalized_at.isoformat(),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResearchEvidenceNormalizationResult":
        """Rehydrate a normalization result from serialized data."""

        return cls(
            evidence_items=tuple(
                EvidenceItem.from_dict(item) for item in payload.get("evidence_items", ())
            ),
            normalized_at=datetime.fromisoformat(
                str(
                    payload.get(
                        "normalized_at",
                        datetime.fromtimestamp(0, UTC).isoformat(),
                    )
                )
            ),
            schema_version=int(payload.get("schema_version", RESEARCH_SCHEMA_VERSION)),
        )


class ResearchEvidenceNormalizer:
    """Normalize and rank fetched research evidence deterministically."""

    def normalize(
        self,
        evidence: Iterable[
            EvidenceItem
            | ResearchFetchResult
            | RepositoryScanResult
            | tuple[EvidenceItem, ...]
            | list[EvidenceItem]
        ],
        *,
        request: ResearchRequest | None = None,
        source_policy: SourcePolicy | None = None,
    ) -> ResearchEvidenceNormalizationResult:
        """Normalize raw fetched evidence into a ranked, deduplicated tuple."""

        self._validate_input(evidence)
        flattened = self._flatten(evidence)
        normalized_items = self._normalize_evidence_items(flattened)
        deduplicated_items = self._deduplicate_evidence(
            normalized_items,
            request=request,
            source_policy=source_policy,
        )
        ranked_items = self._rank_evidence(
            deduplicated_items,
            request=request,
            source_policy=source_policy,
        )
        limited_items = self._apply_limit(ranked_items, request, source_policy)
        return ResearchEvidenceNormalizationResult(evidence_items=limited_items)

    def _validate_input(
        self,
        evidence: Iterable[
            EvidenceItem
            | ResearchFetchResult
            | RepositoryScanResult
            | tuple[EvidenceItem, ...]
            | list[EvidenceItem]
        ],
    ) -> None:
        if isinstance(evidence, (str, bytes)):
            raise MalformedResearchEvidenceError("Evidence must be iterable structured evidence.")

    def _flatten(
        self,
        evidence: Iterable[
            EvidenceItem
            | ResearchFetchResult
            | RepositoryScanResult
            | tuple[EvidenceItem, ...]
            | list[EvidenceItem]
        ],
    ) -> tuple[EvidenceItem, ...]:
        flattened: list[EvidenceItem] = []
        for item in evidence:
            if isinstance(item, EvidenceItem):
                flattened.append(item)
                continue
            if isinstance(item, ResearchFetchResult):
                flattened.extend(item.evidence_items)
                continue
            if isinstance(item, RepositoryScanResult):
                flattened.extend(item.evidence_items)
                continue
            raise MalformedResearchEvidenceError(
                f"Unsupported evidence item type: {item.__class__.__name__}."
            )
        return tuple(flattened)

    def _normalize_evidence_items(self, flattened: tuple[EvidenceItem, ...]) -> tuple[EvidenceItem, ...]:
        normalized: list[EvidenceItem] = []
        for item in flattened:
            normalized_item = self._normalize_item(item)
            if normalized_item is not None:
                normalized.append(normalized_item)
        return tuple(normalized)

    def _deduplicate_evidence(
        self,
        evidence_items: tuple[EvidenceItem, ...],
        *,
        request: ResearchRequest | None,
        source_policy: SourcePolicy | None,
    ) -> tuple[tuple[EvidenceItem, _RankingKey], ...]:
        seen: dict[tuple[str, str, str], tuple[EvidenceItem, _RankingKey]] = {}
        for index, item in enumerate(evidence_items):
            if not self._allowed(item, source_policy):
                continue
            ranking_key = self._build_ranking_key(item, request, source_policy, index)
            dedupe_key = self._dedupe_key(item)
            current = seen.get(dedupe_key)
            if current is None or ranking_key > current[1]:
                seen[dedupe_key] = (item, ranking_key)
        return tuple(seen.values())

    def _rank_evidence(
        self,
        deduplicated_items: tuple[tuple[EvidenceItem, _RankingKey], ...],
        *,
        request: ResearchRequest | None,
        source_policy: SourcePolicy | None,
    ) -> tuple[tuple[EvidenceItem, _RankingKey], ...]:
        return tuple(
            sorted(
                deduplicated_items,
                key=lambda entry: entry[1],
                reverse=True,
            )
        )

    def _apply_limit(
        self,
        ranked_items: tuple[tuple[EvidenceItem, _RankingKey], ...],
        request: ResearchRequest | None,
        source_policy: SourcePolicy | None,
    ) -> tuple[EvidenceItem, ...]:
        limit = self._resolve_limit(request, source_policy, len(ranked_items))
        return tuple(item for item, _ in ranked_items[:limit])

    def _dedupe_key(self, item: EvidenceItem) -> tuple[str, str, str]:
        return (
            item.source_type.value,
            item.source_ref,
            item.excerpt,
        )

    def _normalize_item(self, item: EvidenceItem) -> EvidenceItem | None:
        if not isinstance(item, EvidenceItem):
            raise MalformedResearchEvidenceError("Evidence normalization requires EvidenceItem objects.")
        source_ref = self._normalize_source_ref(item.source_ref)
        excerpt = self._normalize_excerpt(item.excerpt)
        provenance = self._normalize_provenance(item.provenance)
        relevance_score = self._clamp_score(item.relevance_score)
        confidence = self._clamp_score(item.confidence)
        return EvidenceItem(
            evidence_id=item.evidence_id,
            source_type=item.source_type,
            source_ref=source_ref,
            excerpt=excerpt,
            relevance_score=relevance_score,
            confidence=confidence,
            freshness=item.freshness if isinstance(item.freshness, EvidenceFreshness) else EvidenceFreshness(str(item.freshness)),
            provenance=provenance,
            schema_version=item.schema_version,
        )

    def _normalize_source_ref(self, value: Any) -> str:
        return " ".join(str(value).strip().replace("\\", "/").split())

    def _normalize_excerpt(self, value: Any) -> str:
        text = str(value).replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.rstrip() for line in text.split("\n")]
        return "\n".join(lines).strip()

    def _normalize_provenance(self, provenance: EvidenceProvenance) -> EvidenceProvenance:
        if not isinstance(provenance, EvidenceProvenance):
            raise MalformedResearchEvidenceError("Evidence provenance must be an EvidenceProvenance.")
        timestamp = provenance.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        else:
            timestamp = timestamp.astimezone(UTC)
        line_range = (
            tuple(int(item) for item in provenance.line_range)
            if provenance.line_range is not None
            else None
        )
        return EvidenceProvenance(
            tool=" ".join(provenance.tool.strip().split()),
            timestamp=timestamp,
            line_range=line_range,
            schema_version=provenance.schema_version,
        )

    def _allowed(
        self,
        item: EvidenceItem,
        source_policy: SourcePolicy | None,
    ) -> bool:
        if source_policy is None:
            return True
        if source_policy.allowed_sources and item.source_type not in source_policy.allowed_sources:
            return False
        if item.source_type in source_policy.blocked_sources:
            return False
        return True

    def _build_ranking_key(
        self,
        item: EvidenceItem,
        request: ResearchRequest | None,
        source_policy: SourcePolicy | None,
        index: int,
    ) -> _RankingKey:
        source_weight = self._source_weight(item, source_policy)
        freshness_weight = self._freshness_weight(item.freshness)
        relevance = self._clamp_score(item.relevance_score)
        confidence = self._clamp_score(item.confidence)
        precision = -len(item.excerpt)
        request_match = 1.0 if request is not None and self._matches_request(item, request) else 0.0
        source_ref = item.source_ref
        evidence_id = item.evidence_id
        combined = _RankingKey(
            source_score=round(
                source_weight
                + (request_match * _REQUEST_MATCH_WEIGHT)
                + (freshness_weight * _FRESHNESS_WEIGHT)
                + (relevance * _RELEVANCE_WEIGHT)
                + (confidence * _CONFIDENCE_WEIGHT),
                8,
            ),
            request_match_score=round(request_match, 8),
            freshness_score=round(freshness_weight, 8),
            relevance_confidence_score=round(relevance + confidence, 8),
            precision_score=precision,
            source_ref=source_ref,
            evidence_id=evidence_id,
        )
        return combined

    def _resolve_limit(
        self,
        request: ResearchRequest | None,
        source_policy: SourcePolicy | None,
        candidate_count: int,
    ) -> int:
        limits = [candidate_count]
        if request is not None:
            limits.append(max(0, int(request.budget.source_limit)))
        if source_policy is not None:
            limits.append(max(0, int(source_policy.max_evidence_items)))
        return min(limits)

    def _matches_request(self, item: EvidenceItem, request: ResearchRequest) -> bool:
        query_tokens = self._tokenize(request.query_text)
        if not query_tokens:
            return False
        source_text = f"{item.source_ref}\n{item.excerpt}".lower()
        return any(token in source_text for token in query_tokens)

    def _source_weight(self, item: EvidenceItem, source_policy: SourcePolicy | None) -> float:
        if source_policy is None:
            return 0.0
        weight_key = item.source_type.value
        return float(source_policy.source_rank_weights.get(weight_key, 0.0))

    def _freshness_weight(self, freshness: EvidenceFreshness) -> float:
        if freshness == EvidenceFreshness.CURRENT:
            return 1.0
        if freshness == EvidenceFreshness.UNKNOWN:
            return 0.5
        return 0.0

    def _clamp_score(self, value: float) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise MalformedResearchEvidenceError("Evidence scores must be numeric.") from exc
        return max(0.0, min(1.0, numeric))

    def _tokenize(self, value: Any) -> tuple[str, ...]:
        text = str(value).strip().lower()
        if not text:
            return ()
        tokens: list[str] = []
        current: list[str] = []
        for character in text:
            if character.isalnum():
                current.append(character)
                continue
            if current:
                token = "".join(current)
                if len(token) > 1 and token not in tokens:
                    tokens.append(token)
                current = []
        if current:
            token = "".join(current)
            if len(token) > 1 and token not in tokens:
                tokens.append(token)
        return tuple(tokens)


def normalize_research_evidence(
    evidence: Iterable[
        EvidenceItem
        | ResearchFetchResult
        | RepositoryScanResult
        | tuple[EvidenceItem, ...]
        | list[EvidenceItem]
    ],
    *,
    request: ResearchRequest | None = None,
    source_policy: SourcePolicy | None = None,
) -> ResearchEvidenceNormalizationResult:
    """Normalize research evidence using the default normalizer."""

    return ResearchEvidenceNormalizer().normalize(
        evidence,
        request=request,
        source_policy=source_policy,
    )
