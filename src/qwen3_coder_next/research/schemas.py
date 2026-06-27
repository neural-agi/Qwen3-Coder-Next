"""Research schema definitions for Part 4 Step 1."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


RESEARCH_SCHEMA_VERSION = 1


class ResearchTaskType(StrEnum):
    """Supported research request classes."""

    FEATURE = "feature"
    BUG = "bug"
    INVESTIGATION = "investigation"


class SourceType(StrEnum):
    """Supported source categories for research discovery."""

    REPO_FILE = "repo_file"
    REPO_FOLDER = "repo_folder"
    DOC = "doc"
    LOG = "log"
    API_REF = "api_ref"
    ERROR_ARTIFACT = "error_artifact"
    APPROVED_EXTERNAL = "approved_external"


class EvidenceFreshness(StrEnum):
    """Freshness classification for research evidence."""

    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"


class ResearchNextAction(StrEnum):
    """Downstream action recommended by research output."""

    CODE = "code"
    CLARIFY = "clarify"
    EXPAND_RESEARCH = "expand_research"


class ResearchStateStatus(StrEnum):
    """Supported research state lifecycle phases."""

    RECEIVED = "received"
    CLASSIFIED = "classified"
    SOURCES_SELECTED = "sources_selected"
    EVIDENCE_GATHERED = "evidence_gathered"
    EVIDENCE_NORMALIZED = "evidence_normalized"
    PACKET_BUILT = "packet_built"
    HANDOFF_READY = "handoff_ready"
    NEEDS_CLARIFICATION = "needs_clarification"


@dataclass(frozen=True, slots=True)
class ResearchBudget:
    """Deterministic budget constraints for a research request."""

    time_ms: int = 30_000
    source_limit: int = 20
    snippet_limit: int = 1_200
    schema_version: int = RESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the budget into a deterministic mapping."""

        return {
            "time_ms": self.time_ms,
            "source_limit": self.source_limit,
            "snippet_limit": self.snippet_limit,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchBudget":
        """Rehydrate a budget from serialized data."""

        return cls(
            time_ms=int(payload.get("time_ms", 30_000)),
            source_limit=int(payload.get("source_limit", 20)),
            snippet_limit=int(payload.get("snippet_limit", 1_200)),
            schema_version=int(payload.get("schema_version", RESEARCH_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class ResearchRequest:
    """Normalized research request handed in from planning."""

    request_id: str
    task_type: ResearchTaskType
    target_repo: str
    query_text: str
    constraints: tuple[str, ...] = ()
    hints: tuple[str, ...] = ()
    budget: ResearchBudget = field(default_factory=ResearchBudget)
    schema_version: int = RESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the request into a deterministic mapping."""

        return {
            "request_id": self.request_id,
            "task_type": self.task_type.value,
            "target_repo": self.target_repo,
            "query_text": self.query_text,
            "constraints": list(self.constraints),
            "hints": list(self.hints),
            "budget": self.budget.to_dict(),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchRequest":
        """Rehydrate a request from serialized data."""

        return cls(
            request_id=str(payload["request_id"]),
            task_type=ResearchTaskType(str(payload["task_type"])),
            target_repo=str(payload["target_repo"]),
            query_text=str(payload["query_text"]),
            constraints=tuple(str(item) for item in payload.get("constraints", ())),
            hints=tuple(str(item) for item in payload.get("hints", ())),
            budget=ResearchBudget.from_dict(dict(payload.get("budget", {}))),
            schema_version=int(payload.get("schema_version", RESEARCH_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class SourceHandle:
    """Typed pointer to an allowed research source."""

    source_id: str
    source_type: SourceType
    source_ref: str
    display_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = RESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the source handle into a deterministic mapping."""

        return {
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "source_ref": self.source_ref,
            "display_name": self.display_name,
            "metadata": dict(self.metadata),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceHandle":
        """Rehydrate a source handle from serialized data."""

        return cls(
            source_id=str(payload["source_id"]),
            source_type=SourceType(str(payload["source_type"])),
            source_ref=str(payload["source_ref"]),
            display_name=str(payload.get("display_name", "")),
            metadata=dict(payload.get("metadata", {})),
            schema_version=int(payload.get("schema_version", RESEARCH_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class EvidenceProvenance:
    """Provenance metadata for a reusable evidence item."""

    tool: str
    timestamp: datetime = field(default_factory=lambda: datetime.fromtimestamp(0, UTC))
    line_range: tuple[int, int] | None = None
    schema_version: int = RESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the provenance into a deterministic mapping."""

        return {
            "tool": self.tool,
            "timestamp": self.timestamp.isoformat(),
            "line_range": list(self.line_range) if self.line_range is not None else None,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceProvenance":
        """Rehydrate provenance metadata from serialized data."""

        line_range = payload.get("line_range")
        return cls(
            tool=str(payload["tool"]),
            timestamp=datetime.fromisoformat(
                str(
                    payload.get(
                        "timestamp",
                        datetime.fromtimestamp(0, UTC).isoformat(),
                    )
                )
            ),
            line_range=tuple(int(item) for item in line_range) if line_range is not None else None,
            schema_version=int(payload.get("schema_version", RESEARCH_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    """Single reusable fact, snippet, or error detail with provenance."""

    evidence_id: str
    source_type: SourceType
    source_ref: str
    excerpt: str
    relevance_score: float
    confidence: float
    freshness: EvidenceFreshness
    provenance: EvidenceProvenance
    schema_version: int = RESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the evidence item into a deterministic mapping."""

        return {
            "evidence_id": self.evidence_id,
            "source_type": self.source_type.value,
            "source_ref": self.source_ref,
            "excerpt": self.excerpt,
            "relevance_score": self.relevance_score,
            "confidence": self.confidence,
            "freshness": self.freshness.value,
            "provenance": self.provenance.to_dict(),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceItem":
        """Rehydrate an evidence item from serialized data."""

        return cls(
            evidence_id=str(payload["evidence_id"]),
            source_type=SourceType(str(payload["source_type"])),
            source_ref=str(payload["source_ref"]),
            excerpt=str(payload["excerpt"]),
            relevance_score=float(payload["relevance_score"]),
            confidence=float(payload["confidence"]),
            freshness=EvidenceFreshness(str(payload["freshness"])),
            provenance=EvidenceProvenance.from_dict(dict(payload["provenance"])),
            schema_version=int(payload.get("schema_version", RESEARCH_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class ResearchPacket:
    """Final research packet consumed by downstream agents."""

    request_id: str
    summary: str
    evidence: tuple[EvidenceItem, ...]
    recommended_next_action: ResearchNextAction
    confidence: float
    open_questions: tuple[str, ...] = ()
    citations: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    schema_version: int = RESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the packet into a deterministic mapping."""

        return {
            "request_id": self.request_id,
            "summary": self.summary,
            "open_questions": list(self.open_questions),
            "evidence": [item.to_dict() for item in self.evidence],
            "recommended_next_action": self.recommended_next_action.value,
            "confidence": self.confidence,
            "citations": list(self.citations),
            "artifacts": list(self.artifacts),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchPacket":
        """Rehydrate a packet from serialized data."""

        return cls(
            request_id=str(payload["request_id"]),
            summary=str(payload["summary"]),
            evidence=tuple(EvidenceItem.from_dict(item) for item in payload.get("evidence", ())),
            recommended_next_action=ResearchNextAction(
                str(payload["recommended_next_action"])
            ),
            confidence=float(payload["confidence"]),
            open_questions=tuple(str(item) for item in payload.get("open_questions", ())),
            citations=tuple(str(item) for item in payload.get("citations", ())),
            artifacts=tuple(str(item) for item in payload.get("artifacts", ())),
            schema_version=int(payload.get("schema_version", RESEARCH_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    """Ruleset governing legal, preferred, and blocked research sources."""

    allowed_sources: tuple[SourceType, ...] = ()
    preferred_sources: tuple[SourceType, ...] = ()
    blocked_sources: tuple[SourceType, ...] = ()
    source_rank_weights: dict[str, float] = field(default_factory=dict)
    max_evidence_items: int = 20
    max_snippet_chars: int = 1_200
    cache_ttl_minutes: int = 60
    schema_version: int = RESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the source policy into a deterministic mapping."""

        return {
            "allowed_sources": [item.value for item in self.allowed_sources],
            "preferred_sources": [item.value for item in self.preferred_sources],
            "blocked_sources": [item.value for item in self.blocked_sources],
            "source_rank_weights": {
                key: self.source_rank_weights[key]
                for key in sorted(self.source_rank_weights)
            },
            "max_evidence_items": self.max_evidence_items,
            "max_snippet_chars": self.max_snippet_chars,
            "cache_ttl_minutes": self.cache_ttl_minutes,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourcePolicy":
        """Rehydrate a source policy from serialized data."""

        return cls(
            allowed_sources=tuple(SourceType(str(item)) for item in payload.get("allowed_sources", ())),
            preferred_sources=tuple(
                SourceType(str(item)) for item in payload.get("preferred_sources", ())
            ),
            blocked_sources=tuple(
                SourceType(str(item)) for item in payload.get("blocked_sources", ())
            ),
            source_rank_weights={
                str(key): float(value)
                for key, value in dict(payload.get("source_rank_weights", {})).items()
            },
            max_evidence_items=int(payload.get("max_evidence_items", 20)),
            max_snippet_chars=int(payload.get("max_snippet_chars", 1_200)),
            cache_ttl_minutes=int(payload.get("cache_ttl_minutes", 60)),
            schema_version=int(payload.get("schema_version", RESEARCH_SCHEMA_VERSION)),
        )
