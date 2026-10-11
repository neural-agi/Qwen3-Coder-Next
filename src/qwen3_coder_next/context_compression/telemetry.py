"""Deterministic metadata-only telemetry for Part 11 Step 8."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True, slots=True)
class CompressionTelemetryEvent:
    event_type: str
    fields: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.event_type, str) or not self.event_type.strip():
            raise ValueError("event_type must be non-empty text.")
        if any(not isinstance(key, str) or not key.strip() or not isinstance(value, str) for key, value in self.fields):
            raise ValueError("telemetry fields must be text key/value pairs.")
        object.__setattr__(self, "event_type", self.event_type.strip())
        object.__setattr__(self, "fields", tuple(sorted(self.fields)))

    def to_dict(self) -> dict[str, object]:
        return {"event_type": self.event_type, "fields": {key: value for key, value in self.fields}}


class CompressionTelemetry:
    """In-process recorder; no timestamps, excerpts, network, or external sink."""

    def __init__(self) -> None:
        self._events: list[CompressionTelemetryEvent] = []

    @property
    def events(self) -> tuple[CompressionTelemetryEvent, ...]:
        return tuple(self._events)

    def record(self, event_type: str, fields: Mapping[str, object] | None = None) -> CompressionTelemetryEvent:
        values = fields or {}
        if not isinstance(values, Mapping):
            raise ValueError("fields must be a mapping.")
        normalized = tuple((str(key), str(value)) for key, value in values.items())
        event = CompressionTelemetryEvent(event_type, normalized)
        self._events.append(event)
        return event


__all__ = ["CompressionTelemetry", "CompressionTelemetryEvent"]
