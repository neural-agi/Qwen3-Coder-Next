"""Immutable, deterministic contracts for Part 11 Step 1."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping


CONTEXT_COMPRESSION_SCHEMA_VERSION = 1


def _text(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f"{name} must be non-empty text.")
    return value.strip() if not allow_empty else value


def _texts(value: object, name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must be a collection of text.")
    try:
        items = tuple(value or ())  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValueError(f"{name} must be a collection of text.") from exc
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise ValueError(f"{name} contains invalid text.")
    return tuple(sorted({item.strip() for item in items}))


def _non_negative_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer.")
    return value


def _positive_int(value: object, name: str) -> int:
    result = _non_negative_int(value, name)
    if result == 0:
        raise ValueError(f"{name} must be a positive integer.")
    return result


def _unit_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1.")
    return float(value)


def _provenance_map(value: object) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        raise ValueError("provenance_map must be a mapping.")
    if not isinstance(value, Mapping):
        raise ValueError("provenance_map must be a mapping.")
    entries: list[tuple[str, tuple[str, ...]]] = []
    for source_id, locations in value.items():
        source = _text(source_id, "provenance_map source_id")
        entries.append((source, _texts(locations, "provenance_map locations")))
    return tuple(sorted(entries, key=lambda item: item[0]))


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(prefix: str, value: Mapping[str, Any]) -> str:
    return f"{prefix}:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ContextRequest:
    task_id: str
    agent_role: str
    intent: str
    token_budget: int
    seed_sources: tuple[str, ...] = field(default_factory=tuple)
    freshness_window: int = 0
    schema_version: int = CONTEXT_COMPRESSION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("task_id", "agent_role", "intent"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "token_budget", _positive_int(self.token_budget, "token_budget"))
        object.__setattr__(self, "seed_sources", _texts(self.seed_sources, "seed_sources"))
        object.__setattr__(self, "freshness_window", _non_negative_int(self.freshness_window, "freshness_window"))

    def to_dict(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "agent_role": self.agent_role, "intent": self.intent, "token_budget": self.token_budget, "seed_sources": list(self.seed_sources), "freshness_window": self.freshness_window, "schema_version": self.schema_version}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ContextRequest":
        if not isinstance(payload, Mapping):
            raise ValueError("context request payload must be a mapping.")
        return cls(payload["task_id"], payload["agent_role"], payload["intent"], payload["token_budget"], payload.get("seed_sources", ()), payload.get("freshness_window", 0), payload.get("schema_version", CONTEXT_COMPRESSION_SCHEMA_VERSION))


@dataclass(frozen=True, slots=True)
class EvidenceChunk:
    source_id: str
    location: str
    excerpt: str
    score: float
    recency: float
    provenance: tuple[str, ...] = field(default_factory=tuple)
    schema_version: int = CONTEXT_COMPRESSION_SCHEMA_VERSION
    retrieval_timestamp: str | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        for name in ("source_id", "location", "excerpt"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "score", _unit_float(self.score, "score"))
        object.__setattr__(self, "recency", _unit_float(self.recency, "recency"))
        object.__setattr__(self, "provenance", _texts(self.provenance, "provenance"))
        if self.retrieval_timestamp is not None and (not isinstance(self.retrieval_timestamp, str) or not self.retrieval_timestamp.strip()):
            raise ValueError("retrieval_timestamp must be non-empty text when provided.")
        if self.retrieval_timestamp is not None:
            object.__setattr__(self, "retrieval_timestamp", self.retrieval_timestamp.strip())
        if self.confidence is not None:
            object.__setattr__(self, "confidence", _unit_float(self.confidence, "confidence"))

    def to_dict(self) -> dict[str, Any]:
        return {"source_id": self.source_id, "location": self.location, "excerpt": self.excerpt, "score": self.score, "recency": self.recency, "provenance": list(self.provenance), "schema_version": self.schema_version, "retrieval_timestamp": self.retrieval_timestamp, "confidence": self.confidence}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EvidenceChunk":
        if not isinstance(payload, Mapping):
            raise ValueError("evidence chunk payload must be a mapping.")
        return cls(payload["source_id"], payload["location"], payload["excerpt"], payload["score"], payload["recency"], payload.get("provenance", ()), payload.get("schema_version", CONTEXT_COMPRESSION_SCHEMA_VERSION), payload.get("retrieval_timestamp"), payload.get("confidence"))


@dataclass(frozen=True, slots=True)
class ContextPackage:
    package_id: str
    task_id: str
    selected_chunks: tuple[EvidenceChunk, ...] = field(default_factory=tuple)
    compressed_brief: str = ""
    budget_used: int = 0
    omissions: tuple[str, ...] = field(default_factory=tuple)
    provenance_map: tuple[tuple[str, tuple[str, ...]], ...] = field(default_factory=tuple)
    schema_version: int = CONTEXT_COMPRESSION_SCHEMA_VERSION
    coverage_notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "package_id", _text(self.package_id, "package_id"))
        object.__setattr__(self, "task_id", _text(self.task_id, "task_id"))
        if isinstance(self.selected_chunks, (str, bytes)) or any(not isinstance(item, EvidenceChunk) for item in self.selected_chunks):
            raise ValueError("selected_chunks contains an invalid EvidenceChunk.")
        object.__setattr__(self, "selected_chunks", tuple(self.selected_chunks))
        object.__setattr__(self, "compressed_brief", _text(self.compressed_brief, "compressed_brief", allow_empty=True))
        object.__setattr__(self, "budget_used", _non_negative_int(self.budget_used, "budget_used"))
        object.__setattr__(self, "omissions", _texts(self.omissions, "omissions"))
        object.__setattr__(self, "provenance_map", _provenance_map(dict(self.provenance_map)))
        object.__setattr__(self, "coverage_notes", _texts(self.coverage_notes, "coverage_notes"))

    def to_dict(self) -> dict[str, Any]:
        return {"package_id": self.package_id, "task_id": self.task_id, "selected_chunks": [item.to_dict() for item in self.selected_chunks], "compressed_brief": self.compressed_brief, "budget_used": self.budget_used, "omissions": list(self.omissions), "provenance_map": {source: list(locations) for source, locations in self.provenance_map}, "schema_version": self.schema_version, "coverage_notes": list(self.coverage_notes)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ContextPackage":
        if not isinstance(payload, Mapping):
            raise ValueError("context package payload must be a mapping.")
        return cls(payload["package_id"], payload["task_id"], tuple(EvidenceChunk.from_dict(item) for item in payload.get("selected_chunks", ())), payload.get("compressed_brief", ""), payload.get("budget_used", 0), payload.get("omissions", ()), payload.get("provenance_map", {}), payload.get("schema_version", CONTEXT_COMPRESSION_SCHEMA_VERSION), payload.get("coverage_notes", ()))


@dataclass(frozen=True, slots=True)
class BudgetReport:
    requested_budget: int
    used_budget: int
    reserved_budget: int
    dropped_sources: tuple[str, ...] = field(default_factory=tuple)
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    schema_version: int = CONTEXT_COMPRESSION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "requested_budget", _non_negative_int(self.requested_budget, "requested_budget"))
        object.__setattr__(self, "used_budget", _non_negative_int(self.used_budget, "used_budget"))
        object.__setattr__(self, "reserved_budget", _non_negative_int(self.reserved_budget, "reserved_budget"))
        if self.used_budget + self.reserved_budget > self.requested_budget:
            raise ValueError("used_budget plus reserved_budget exceeds requested_budget.")
        object.__setattr__(self, "dropped_sources", _texts(self.dropped_sources, "dropped_sources"))
        object.__setattr__(self, "reason_codes", _texts(self.reason_codes, "reason_codes"))

    def to_dict(self) -> dict[str, Any]:
        return {"requested_budget": self.requested_budget, "used_budget": self.used_budget, "reserved_budget": self.reserved_budget, "dropped_sources": list(self.dropped_sources), "reason_codes": list(self.reason_codes), "schema_version": self.schema_version}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BudgetReport":
        if not isinstance(payload, Mapping):
            raise ValueError("budget report payload must be a mapping.")
        return cls(payload["requested_budget"], payload["used_budget"], payload["reserved_budget"], payload.get("dropped_sources", ()), payload.get("reason_codes", ()), payload.get("schema_version", CONTEXT_COMPRESSION_SCHEMA_VERSION))


@dataclass(frozen=True, slots=True)
class CompressionConfig:
    max_tokens: int
    min_source_coverage: float
    summary_style: str
    dedupe_threshold: float
    freshness_priority: float
    schema_version: int = CONTEXT_COMPRESSION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "max_tokens", _positive_int(self.max_tokens, "max_tokens"))
        object.__setattr__(self, "min_source_coverage", _unit_float(self.min_source_coverage, "min_source_coverage"))
        object.__setattr__(self, "summary_style", _text(self.summary_style, "summary_style"))
        object.__setattr__(self, "dedupe_threshold", _unit_float(self.dedupe_threshold, "dedupe_threshold"))
        object.__setattr__(self, "freshness_priority", _unit_float(self.freshness_priority, "freshness_priority"))

    def to_dict(self) -> dict[str, Any]:
        return {"max_tokens": self.max_tokens, "min_source_coverage": self.min_source_coverage, "summary_style": self.summary_style, "dedupe_threshold": self.dedupe_threshold, "freshness_priority": self.freshness_priority, "schema_version": self.schema_version}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CompressionConfig":
        if not isinstance(payload, Mapping):
            raise ValueError("compression config payload must be a mapping.")
        return cls(payload["max_tokens"], payload["min_source_coverage"], payload["summary_style"], payload["dedupe_threshold"], payload["freshness_priority"], payload.get("schema_version", CONTEXT_COMPRESSION_SCHEMA_VERSION))


def context_request_fingerprint(request: ContextRequest) -> str:
    if not isinstance(request, ContextRequest):
        raise ValueError("request must be a ContextRequest.")
    return _digest("context-request", request.to_dict())


def compression_config_fingerprint(config: CompressionConfig) -> str:
    if not isinstance(config, CompressionConfig):
        raise ValueError("config must be a CompressionConfig.")
    return _digest("compression-config", config.to_dict())


def canonical_package_id(task_id: str, request_fingerprint: str, source_fingerprints: object, policy_version: str) -> str:
    payload = {"task_id": _text(task_id, "task_id"), "request_fingerprint": _text(request_fingerprint, "request_fingerprint"), "source_fingerprints": list(_texts(source_fingerprints, "source_fingerprints")), "policy_version": _text(policy_version, "policy_version")}
    return _digest("context-package", payload)
