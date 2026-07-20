"""Deterministic research packet assembly for Part 4 Step 6."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Iterable, Mapping

from qwen3_coder_next.research.evidence import (
    ResearchEvidenceNormalizationResult,
    ResearchEvidenceNormalizer,
)
from qwen3_coder_next.research.fetchers import ResearchFetchResult
from qwen3_coder_next.research.scanner import RepositoryScanResult
from qwen3_coder_next.research.schemas import (
    RESEARCH_SCHEMA_VERSION,
    EvidenceItem,
    ResearchNextAction,
    ResearchPacket,
    ResearchRequest,
    SourcePolicy,
)


class ResearchPacketAssemblyError(ValueError):
    """Base error for research packet assembly failures."""


class MalformedResearchPacketInputError(ResearchPacketAssemblyError):
    """Raised when packet assembly receives malformed inputs."""


_REQUEST_ARTIFACT_PREFIX = "request:"
_SOURCE_POLICY_ARTIFACT_PREFIX = "source-policy:"
_EVIDENCE_ARTIFACT_PREFIX = "evidence:"

_PACKET_CODE_CONFIDENCE = 0.85
_PACKET_CLARIFY_CONFIDENCE = 0.6


class _PacketEvidenceNormalizer:
    """Internal composition point for packet evidence normalization."""

    def __init__(self, normalizer: ResearchEvidenceNormalizer | None = None) -> None:
        self._normalizer = normalizer or ResearchEvidenceNormalizer()

    def normalize(
        self,
        evidence: (
            ResearchEvidenceNormalizationResult
            | ResearchFetchResult
            | RepositoryScanResult
            | Iterable[EvidenceItem]
        ),
    ) -> tuple[EvidenceItem, ...]:
        if isinstance(evidence, ResearchEvidenceNormalizationResult):
            return evidence.evidence_items
        if isinstance(evidence, ResearchFetchResult):
            return self._normalizer.normalize(evidence.evidence_items).evidence_items
        if isinstance(evidence, RepositoryScanResult):
            return self._normalizer.normalize(evidence.evidence_items).evidence_items
        normalized: list[EvidenceItem] = []
        for item in evidence:
            if not isinstance(item, EvidenceItem):
                raise MalformedResearchPacketInputError(
                    "Packet assembly requires EvidenceItem objects."
                )
            normalized.append(item)
        return tuple(normalized)


class _PacketSummaryBuilder:
    """Build deterministic structural packet summaries."""

    @staticmethod
    def build(request: ResearchRequest, evidence_items: tuple[EvidenceItem, ...]) -> str:
        evidence_count = len(evidence_items)
        subject = request.target_repo or request.request_id
        return "|".join(
            (
                f"task_type={request.task_type.value}",
                f"request_id={request.request_id}",
                f"subject={subject}",
                f"query_text={request.query_text}",
                f"evidence_count={evidence_count}",
            )
        )


class _PacketOutcomeStrategy:
    """Deterministic packet outcome heuristics."""

    @staticmethod
    def confidence(evidence_items: tuple[EvidenceItem, ...]) -> float:
        if not evidence_items:
            return 0.0
        total = sum((item.relevance_score + item.confidence) / 2.0 for item in evidence_items)
        return round(max(0.0, min(1.0, total / len(evidence_items))), 8)

    @staticmethod
    def next_action(
        evidence_items: tuple[EvidenceItem, ...],
        confidence: float,
    ) -> ResearchNextAction:
        if not evidence_items:
            return ResearchNextAction.EXPAND_RESEARCH
        if confidence >= _PACKET_CODE_CONFIDENCE:
            return ResearchNextAction.CODE
        if confidence >= _PACKET_CLARIFY_CONFIDENCE:
            return ResearchNextAction.CLARIFY
        return ResearchNextAction.EXPAND_RESEARCH

    @staticmethod
    def open_questions(
        request: ResearchRequest,
        evidence_items: tuple[EvidenceItem, ...],
    ) -> tuple[str, ...]:
        if evidence_items:
            return ()
        return (f"Gather additional evidence for {request.query_text}.",)


class _PacketArtifactBuilder:
    """Build deterministic packet artifact references."""

    def build(
        self,
        request: ResearchRequest,
        source_policy: SourcePolicy | None,
        evidence_items: tuple[EvidenceItem, ...],
    ) -> tuple[str, ...]:
        artifacts: list[str] = [f"{_REQUEST_ARTIFACT_PREFIX}{request.request_id}"]
        if source_policy is not None:
            artifacts.append(
                f"{_SOURCE_POLICY_ARTIFACT_PREFIX}{self._policy_digest(source_policy)}"
            )
        for item in evidence_items:
            artifacts.append(f"{_EVIDENCE_ARTIFACT_PREFIX}{item.evidence_id}")
        return tuple(artifacts)

    def _policy_digest(self, source_policy: SourcePolicy) -> str:
        canonical_json = json.dumps(
            source_policy.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return sha256(canonical_json.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ResearchPacketAssembler:
    """Assemble deterministic research packets from normalized evidence."""

    _evidence_normalizer: _PacketEvidenceNormalizer = _PacketEvidenceNormalizer()
    _summary_builder: _PacketSummaryBuilder = _PacketSummaryBuilder()
    _outcome_strategy: _PacketOutcomeStrategy = _PacketOutcomeStrategy()
    _artifact_builder: _PacketArtifactBuilder = _PacketArtifactBuilder()

    def assemble(
        self,
        request: ResearchRequest,
        evidence: (
            ResearchEvidenceNormalizationResult
            | ResearchFetchResult
            | RepositoryScanResult
            | Iterable[EvidenceItem]
        ),
        *,
        source_policy: SourcePolicy | None = None,
    ) -> ResearchPacket:
        """Assemble a stable research packet for downstream consumers."""

        self._validate_input(request, evidence, source_policy)
        evidence_items = self._normalize_evidence_items(evidence)
        selected_items = self._select_evidence_items(request, evidence_items, source_policy)
        summary = self._summary_builder.build(request, selected_items)
        citations = self._build_citations(selected_items)
        artifacts = self._artifact_builder.build(request, source_policy, selected_items)
        confidence = self._outcome_strategy.confidence(selected_items)
        next_action = self._outcome_strategy.next_action(selected_items, confidence)
        open_questions = self._outcome_strategy.open_questions(request, selected_items)
        return ResearchPacket(
            request_id=request.request_id,
            summary=summary,
            evidence=selected_items,
            recommended_next_action=next_action,
            confidence=confidence,
            open_questions=open_questions,
            citations=citations,
            artifacts=artifacts,
            schema_version=RESEARCH_SCHEMA_VERSION,
        )

    def _validate_input(
        self,
        request: ResearchRequest,
        evidence: (
            ResearchEvidenceNormalizationResult
            | ResearchFetchResult
            | RepositoryScanResult
            | Iterable[EvidenceItem]
        ),
        source_policy: SourcePolicy | None,
    ) -> None:
        if not isinstance(request, ResearchRequest):
            raise MalformedResearchPacketInputError("Packet assembly requires a ResearchRequest.")
        if source_policy is not None and not isinstance(source_policy, SourcePolicy):
            raise MalformedResearchPacketInputError("Packet assembly requires a SourcePolicy.")
        if isinstance(evidence, (str, bytes)):
            raise MalformedResearchPacketInputError(
                "Packet evidence must be iterable structured evidence."
            )

    def _normalize_evidence_items(
        self,
        evidence: (
            ResearchEvidenceNormalizationResult
            | ResearchFetchResult
            | RepositoryScanResult
            | Iterable[EvidenceItem]
        ),
    ) -> tuple[EvidenceItem, ...]:
        if isinstance(evidence, ResearchEvidenceNormalizationResult):
            return evidence.evidence_items
        if isinstance(evidence, ResearchFetchResult):
            return self._evidence_normalizer.normalize(evidence.evidence_items)
        if isinstance(evidence, RepositoryScanResult):
            return self._evidence_normalizer.normalize(evidence.evidence_items)
        return self._evidence_normalizer.normalize(tuple(evidence)).evidence_items

    def _select_evidence_items(
        self,
        request: ResearchRequest,
        evidence_items: tuple[EvidenceItem, ...],
        source_policy: SourcePolicy | None,
    ) -> tuple[EvidenceItem, ...]:
        limit = len(evidence_items)
        limit = min(limit, max(0, int(request.budget.source_limit)))
        if source_policy is not None:
            limit = min(limit, max(0, int(source_policy.max_evidence_items)))
        return tuple(evidence_items[:limit])

    def _build_citations(self, evidence_items: tuple[EvidenceItem, ...]) -> tuple[str, ...]:
        citations: list[str] = []
        for item in evidence_items:
            citation = item.source_ref
            if item.provenance.line_range is not None:
                start, end = item.provenance.line_range
                citation = f"{citation}:{start}-{end}"
            citations.append(citation)
        return tuple(citations)


def assemble_research_packet(
    request: ResearchRequest,
    evidence: (
        ResearchEvidenceNormalizationResult
        | ResearchFetchResult
        | RepositoryScanResult
        | Iterable[EvidenceItem]
    ),
    *,
    source_policy: SourcePolicy | None = None,
) -> ResearchPacket:
    """Assemble a research packet using the default assembler."""

    return ResearchPacketAssembler().assemble(
        request,
        evidence,
        source_policy=source_policy,
    )
