"""Deterministic source-plan resolution without retrieval or store access."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from qwen3_coder_next.context_compression.schemas import ContextRequest


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text.")
    return value.strip()


@dataclass(frozen=True, slots=True)
class SourceSpec:
    """Caller-supplied availability metadata for one existing source boundary."""

    source_id: str
    source_type: str
    fingerprint: str
    available: bool = True
    freshness_window: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _text(self.source_id, "source_id"))
        object.__setattr__(self, "source_type", _text(self.source_type, "source_type"))
        object.__setattr__(self, "fingerprint", _text(self.fingerprint, "fingerprint"))
        if not isinstance(self.available, bool):
            raise ValueError("available must be a boolean.")
        if not isinstance(self.freshness_window, int) or isinstance(self.freshness_window, bool) or self.freshness_window < 0:
            raise ValueError("freshness_window must be a non-negative integer.")


@dataclass(frozen=True, slots=True)
class SourcePlanEntry:
    source_id: str
    source_type: str
    fingerprint: str
    priority: float
    status: str = "available"
    reason: str = ""

    def __post_init__(self) -> None:
        for name in ("source_id", "source_type", "fingerprint"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if not isinstance(self.priority, (int, float)) or isinstance(self.priority, bool) or not 0 <= self.priority <= 1:
            raise ValueError("priority must be between 0 and 1.")
        object.__setattr__(self, "priority", float(self.priority))
        object.__setattr__(self, "status", _text(self.status, "status"))
        object.__setattr__(self, "reason", self.reason if isinstance(self.reason, str) else _text(self.reason, "reason"))


@dataclass(frozen=True, slots=True)
class SourcePlan:
    entries: tuple[SourcePlanEntry, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if isinstance(self.entries, (str, bytes)) or any(not isinstance(item, SourcePlanEntry) for item in self.entries):
            raise ValueError("entries contains an invalid SourcePlanEntry.")
        ordered = tuple(sorted(self.entries, key=lambda item: (-item.priority, item.source_id, item.source_type, item.fingerprint)))
        if len({item.source_id for item in ordered}) != len(ordered):
            raise ValueError("source plan contains duplicate source IDs.")
        object.__setattr__(self, "entries", ordered)


class SourceResolver:
    """Resolve explicit source metadata into a stable plan; never retrieves evidence."""

    def resolve(self, request: ContextRequest, sources: Iterable[SourceSpec]) -> SourcePlan:
        if not isinstance(request, ContextRequest):
            raise ValueError("request must be a ContextRequest.")
        if isinstance(sources, (str, bytes)):
            raise ValueError("sources must be a collection of SourceSpec values.")
        try:
            specs = tuple(sources)
        except TypeError as exc:
            raise ValueError("sources must be a collection of SourceSpec values.") from exc
        if any(not isinstance(item, SourceSpec) for item in specs):
            raise ValueError("sources contains an invalid SourceSpec.")
        by_id = {item.source_id: item for item in specs}
        if len(by_id) != len(specs):
            raise ValueError("sources contains duplicate source IDs.")
        requested = request.seed_sources or tuple(sorted(by_id))
        entries: list[SourcePlanEntry] = []
        for source_id in requested:
            spec = by_id.get(source_id)
            if spec is None:
                entries.append(SourcePlanEntry(source_id, "unknown", "unavailable", 1.0 if request.seed_sources else 0.5, "unavailable", "source_not_configured"))
                continue
            stale = request.freshness_window > spec.freshness_window
            if not spec.available:
                status, reason = "unavailable", "source_unavailable"
            elif stale:
                status, reason = "stale", "source_fingerprint_stale"
            else:
                status, reason = "available", ""
            entries.append(SourcePlanEntry(spec.source_id, spec.source_type, spec.fingerprint, 1.0 if source_id in request.seed_sources else 0.5, status, reason))
        return SourcePlan(tuple(entries))
