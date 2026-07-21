"""Memory schema definitions for Part 5 Step 1."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


MEMORY_SCHEMA_VERSION = 1


class MemoryTier(StrEnum):
    """Supported memory tiers."""

    WORKING = "working"
    SESSION = "session"
    PROJECT = "project"
    GLOBAL = "global"


def _ensure_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value


def _ensure_optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _ensure_text(value, field_name)


def _ensure_tuple(value: object, field_name: str) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    if isinstance(value, str):
        raise ValueError(f"{field_name} must not be a string.")
    return tuple(value)  # type: ignore[arg-type]


def _ensure_text_tuple(value: object, field_name: str) -> tuple[str, ...]:
    items = _ensure_tuple(value, field_name)
    normalized: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_name}[{index}] must be a non-empty string.")
        normalized.append(item)
    return tuple(normalized)


def _ensure_mapping(value: object, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        return dict(value)  # type: ignore[arg-type]
    return dict(value)


def _ensure_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a datetime instance.")
    return value


def _ensure_memory_tier(value: object, field_name: str) -> MemoryTier:
    if isinstance(value, MemoryTier):
        return value
    if isinstance(value, str):
        return MemoryTier(value)
    raise ValueError(f"{field_name} must be a memory tier.")


@dataclass(frozen=True, slots=True)
class MemoryItem:
    """Canonical memory record."""

    memory_id: str
    tier: MemoryTier
    subject: str
    content: str
    source: str
    timestamp: datetime = field(default_factory=lambda: datetime.fromtimestamp(0, UTC))
    confidence: str = "unknown"
    tags: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    schema_version: int = MEMORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "memory_id", _ensure_text(self.memory_id, "memory_id"))
        object.__setattr__(self, "tier", _ensure_memory_tier(self.tier, "tier"))
        object.__setattr__(self, "subject", _ensure_text(self.subject, "subject"))
        object.__setattr__(self, "content", _ensure_text(self.content, "content"))
        object.__setattr__(self, "source", _ensure_text(self.source, "source"))
        object.__setattr__(self, "timestamp", _ensure_datetime(self.timestamp, "timestamp"))
        object.__setattr__(self, "confidence", _ensure_text(self.confidence, "confidence"))
        object.__setattr__(self, "tags", _ensure_text_tuple(self.tags, "tags"))
        object.__setattr__(self, "references", _ensure_text_tuple(self.references, "references"))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the memory item into a deterministic mapping."""

        return {
            "memory_id": self.memory_id,
            "tier": self.tier.value,
            "subject": self.subject,
            "content": self.content,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "tags": list(self.tags),
            "references": list(self.references),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryItem":
        """Rehydrate a memory item from serialized data."""

        memory_id = payload.get("memory_id", payload.get("id"))
        if memory_id is None:
            raise KeyError("memory_id")
        return cls(
            memory_id=str(memory_id),
            tier=_ensure_memory_tier(payload["tier"], "tier"),
            subject=str(payload["subject"]),
            content=str(payload["content"]),
            source=str(payload["source"]),
            timestamp=datetime.fromisoformat(
                str(payload.get("timestamp", datetime.fromtimestamp(0, UTC).isoformat()))
            ),
            confidence=str(payload.get("confidence", "unknown")),
            tags=_ensure_text_tuple(payload.get("tags", ()), "tags"),
            references=_ensure_text_tuple(payload.get("references", ()), "references"),
            schema_version=int(payload.get("schema_version", MEMORY_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class MemoryQuery:
    """Structured query for future memory retrieval."""

    query_text: str
    tier_hint: MemoryTier | None = None
    project_id: str | None = None
    session_id: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)
    top_k: int = 10
    schema_version: int = MEMORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "query_text", _ensure_text(self.query_text, "query_text"))
        object.__setattr__(self, "tier_hint", _ensure_memory_tier(self.tier_hint, "tier_hint") if self.tier_hint is not None else None)
        object.__setattr__(self, "project_id", _ensure_optional_text(self.project_id, "project_id"))
        object.__setattr__(self, "session_id", _ensure_optional_text(self.session_id, "session_id"))
        object.__setattr__(self, "filters", _ensure_mapping(self.filters, "filters"))
        if not isinstance(self.top_k, int) or self.top_k <= 0:
            raise ValueError("top_k must be a positive integer.")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the query into a deterministic mapping."""

        return {
            "query_text": self.query_text,
            "tier_hint": self.tier_hint.value if self.tier_hint is not None else None,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "filters": dict(self.filters),
            "top_k": self.top_k,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryQuery":
        """Rehydrate a memory query from serialized data."""

        tier_hint = payload.get("tier_hint")
        return cls(
            query_text=str(payload["query_text"]),
            tier_hint=_ensure_memory_tier(tier_hint, "tier_hint") if tier_hint is not None else None,
            project_id=_ensure_optional_text(payload.get("project_id"), "project_id"),
            session_id=_ensure_optional_text(payload.get("session_id"), "session_id"),
            filters=_ensure_mapping(payload.get("filters"), "filters"),
            top_k=int(payload.get("top_k", 10)),
            schema_version=int(payload.get("schema_version", MEMORY_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class MemoryResult:
    """Ranked memory retrieval result."""

    item: MemoryItem
    score: float
    rationale: str
    retrieval_source: str
    schema_version: int = MEMORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.item, MemoryItem):
            raise ValueError("item must be a MemoryItem instance.")
        object.__setattr__(self, "rationale", _ensure_text(self.rationale, "rationale"))
        object.__setattr__(self, "retrieval_source", _ensure_text(self.retrieval_source, "retrieval_source"))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the memory result into a deterministic mapping."""

        return {
            "item": self.item.to_dict(),
            "score": self.score,
            "rationale": self.rationale,
            "retrieval_source": self.retrieval_source,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryResult":
        """Rehydrate a memory result from serialized data."""

        return cls(
            item=MemoryItem.from_dict(dict(payload["item"])),
            score=float(payload["score"]),
            rationale=str(payload["rationale"]),
            retrieval_source=str(payload["retrieval_source"]),
            schema_version=int(payload.get("schema_version", MEMORY_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class SessionSummary:
    """Durable summary of a session."""

    session_id: str
    goal: str
    outcomes: tuple[str, ...] = ()
    decisions: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    schema_version: int = MEMORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "session_id", _ensure_text(self.session_id, "session_id"))
        object.__setattr__(self, "goal", _ensure_text(self.goal, "goal"))
        object.__setattr__(self, "outcomes", _ensure_text_tuple(self.outcomes, "outcomes"))
        object.__setattr__(self, "decisions", _ensure_text_tuple(self.decisions, "decisions"))
        object.__setattr__(self, "open_questions", _ensure_text_tuple(self.open_questions, "open_questions"))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the summary into a deterministic mapping."""

        return {
            "session_id": self.session_id,
            "goal": self.goal,
            "outcomes": list(self.outcomes),
            "decisions": list(self.decisions),
            "open_questions": list(self.open_questions),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SessionSummary":
        """Rehydrate a session summary from serialized data."""

        return cls(
            session_id=str(payload["session_id"]),
            goal=str(payload["goal"]),
            outcomes=_ensure_text_tuple(payload.get("outcomes", ()), "outcomes"),
            decisions=_ensure_text_tuple(payload.get("decisions", ()), "decisions"),
            open_questions=_ensure_text_tuple(payload.get("open_questions", ()), "open_questions"),
            schema_version=int(payload.get("schema_version", MEMORY_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class ProjectDecision:
    """Versioned project-scoped decision."""

    project_id: str
    decision: str
    rationale: str
    alternatives: tuple[str, ...] = ()
    version: int = 1
    schema_version: int = MEMORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _ensure_text(self.project_id, "project_id"))
        object.__setattr__(self, "decision", _ensure_text(self.decision, "decision"))
        object.__setattr__(self, "rationale", _ensure_text(self.rationale, "rationale"))
        object.__setattr__(self, "alternatives", _ensure_text_tuple(self.alternatives, "alternatives"))
        if not isinstance(self.version, int) or self.version <= 0:
            raise ValueError("version must be a positive integer.")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the decision into a deterministic mapping."""

        return {
            "project_id": self.project_id,
            "decision": self.decision,
            "rationale": self.rationale,
            "alternatives": list(self.alternatives),
            "version": self.version,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProjectDecision":
        """Rehydrate a project decision from serialized data."""

        return cls(
            project_id=str(payload["project_id"]),
            decision=str(payload["decision"]),
            rationale=str(payload["rationale"]),
            alternatives=_ensure_text_tuple(payload.get("alternatives", ()), "alternatives"),
            version=int(payload.get("version", 1)),
            schema_version=int(payload.get("schema_version", MEMORY_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class GlobalPattern:
    """Reusable cross-project pattern."""

    pattern_name: str
    applicability: str
    evidence: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()
    schema_version: int = MEMORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "pattern_name", _ensure_text(self.pattern_name, "pattern_name"))
        object.__setattr__(self, "applicability", _ensure_text(self.applicability, "applicability"))
        object.__setattr__(self, "evidence", _ensure_text_tuple(self.evidence, "evidence"))
        object.__setattr__(self, "caveats", _ensure_text_tuple(self.caveats, "caveats"))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the pattern into a deterministic mapping."""

        return {
            "pattern_name": self.pattern_name,
            "applicability": self.applicability,
            "evidence": list(self.evidence),
            "caveats": list(self.caveats),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GlobalPattern":
        """Rehydrate a global pattern from serialized data."""

        return cls(
            pattern_name=str(payload["pattern_name"]),
            applicability=str(payload["applicability"]),
            evidence=_ensure_text_tuple(payload.get("evidence", ()), "evidence"),
            caveats=_ensure_text_tuple(payload.get("caveats", ()), "caveats"),
            schema_version=int(payload.get("schema_version", MEMORY_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class MemoryEvent:
    """Append-only activity record for memory operations."""

    event_type: str
    actor: str
    payload: dict[str, Any] = field(default_factory=dict)
    references: tuple[str, ...] = ()
    status: str = "recorded"
    schema_version: int = MEMORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", _ensure_text(self.event_type, "event_type"))
        object.__setattr__(self, "actor", _ensure_text(self.actor, "actor"))
        object.__setattr__(self, "payload", _ensure_mapping(self.payload, "payload"))
        object.__setattr__(self, "references", _ensure_text_tuple(self.references, "references"))
        object.__setattr__(self, "status", _ensure_text(self.status, "status"))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the event into a deterministic mapping."""

        return {
            "event_type": self.event_type,
            "actor": self.actor,
            "payload": dict(self.payload),
            "references": list(self.references),
            "status": self.status,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryEvent":
        """Rehydrate a memory event from serialized data."""

        return cls(
            event_type=str(payload["event_type"]),
            actor=str(payload["actor"]),
            payload=_ensure_mapping(payload.get("payload"), "payload"),
            references=_ensure_text_tuple(payload.get("references", ()), "references"),
            status=str(payload.get("status", "recorded")),
            schema_version=int(payload.get("schema_version", MEMORY_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """Lifecycle policy governing memory retention and promotion."""

    tier: MemoryTier
    keep_days: int
    promote_on_signal: tuple[str, ...] = ()
    prune_on_signal: tuple[str, ...] = ()
    schema_version: int = MEMORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "tier", _ensure_memory_tier(self.tier, "tier"))
        if not isinstance(self.keep_days, int) or self.keep_days < 0:
            raise ValueError("keep_days must be a non-negative integer.")
        object.__setattr__(self, "promote_on_signal", _ensure_text_tuple(self.promote_on_signal, "promote_on_signal"))
        object.__setattr__(self, "prune_on_signal", _ensure_text_tuple(self.prune_on_signal, "prune_on_signal"))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the policy into a deterministic mapping."""

        return {
            "tier": self.tier.value,
            "keep_days": self.keep_days,
            "promote_on_signal": list(self.promote_on_signal),
            "prune_on_signal": list(self.prune_on_signal),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RetentionPolicy":
        """Rehydrate a retention policy from serialized data."""

        return cls(
            tier=_ensure_memory_tier(payload["tier"], "tier"),
            keep_days=int(payload.get("keep_days", 0)),
            promote_on_signal=_ensure_text_tuple(payload.get("promote_on_signal", ()), "promote_on_signal"),
            prune_on_signal=_ensure_text_tuple(payload.get("prune_on_signal", ()), "prune_on_signal"),
            schema_version=int(payload.get("schema_version", MEMORY_SCHEMA_VERSION)),
        )
