"""Memory state container for Part 5 Step 1."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

from qwen3_coder_next.memory.schemas import (
    MEMORY_SCHEMA_VERSION,
    GlobalPattern,
    MemoryEvent,
    MemoryItem,
    ProjectDecision,
    RetentionPolicy,
    SessionSummary,
)


def _ensure_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value


def _ensure_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a datetime instance.")
    return value


def _ensure_revision_number(value: object, field_name: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def _ensure_collection(value: object, field_name: str) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    if isinstance(value, str):
        raise ValueError(f"{field_name} must not be a string.")
    return tuple(value)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class MemoryRevision:
    """Immutable record of a memory state revision."""

    revision_id: str
    revision_number: int
    summary: str
    created_at: datetime = field(default_factory=lambda: datetime.fromtimestamp(0, UTC))
    schema_version: int = MEMORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "revision_id", _ensure_text(self.revision_id, "revision_id"))
        object.__setattr__(self, "revision_number", _ensure_revision_number(self.revision_number, "revision_number"))
        object.__setattr__(self, "summary", _ensure_text(self.summary, "summary"))
        object.__setattr__(self, "created_at", _ensure_datetime(self.created_at, "created_at"))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the revision into a deterministic mapping."""

        return {
            "revision_id": self.revision_id,
            "revision_number": self.revision_number,
            "summary": self.summary,
            "created_at": self.created_at.isoformat(),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryRevision":
        """Rehydrate a memory revision from serialized data."""

        return cls(
            revision_id=str(payload["revision_id"]),
            revision_number=int(payload["revision_number"]),
            summary=str(payload["summary"]),
            created_at=datetime.fromisoformat(
                str(
                    payload.get(
                        "created_at",
                        datetime.fromtimestamp(0, UTC).isoformat(),
                    )
                )
            ),
            schema_version=int(payload.get("schema_version", MEMORY_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class MemoryState:
    """Explicit, append-first memory state container."""

    state_id: str
    state_version: int = 1
    memory_items: tuple[MemoryItem, ...] = ()
    session_summaries: tuple[SessionSummary, ...] = ()
    project_decisions: tuple[ProjectDecision, ...] = ()
    global_patterns: tuple[GlobalPattern, ...] = ()
    memory_events: tuple[MemoryEvent, ...] = ()
    retention_policy: RetentionPolicy | None = None
    revision_history: tuple[MemoryRevision, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.fromtimestamp(0, UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.fromtimestamp(0, UTC))

    def __post_init__(self) -> None:
        object.__setattr__(self, "state_id", _ensure_text(self.state_id, "state_id"))
        if not isinstance(self.state_version, int) or self.state_version <= 0:
            raise ValueError("state_version must be a positive integer.")
        object.__setattr__(self, "memory_items", _ensure_collection(self.memory_items, "memory_items"))
        object.__setattr__(self, "session_summaries", _ensure_collection(self.session_summaries, "session_summaries"))
        object.__setattr__(self, "project_decisions", _ensure_collection(self.project_decisions, "project_decisions"))
        object.__setattr__(self, "global_patterns", _ensure_collection(self.global_patterns, "global_patterns"))
        object.__setattr__(self, "memory_events", _ensure_collection(self.memory_events, "memory_events"))
        if self.retention_policy is not None and not isinstance(self.retention_policy, RetentionPolicy):
            raise ValueError("retention_policy must be a RetentionPolicy instance.")
        object.__setattr__(self, "revision_history", _ensure_collection(self.revision_history, "revision_history"))
        object.__setattr__(self, "created_at", _ensure_datetime(self.created_at, "created_at"))
        object.__setattr__(self, "updated_at", _ensure_datetime(self.updated_at, "updated_at"))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the memory state into a deterministic mapping."""

        return {
            "state_id": self.state_id,
            "state_version": self.state_version,
            "memory_items": [item.to_dict() for item in self.memory_items],
            "session_summaries": [item.to_dict() for item in self.session_summaries],
            "project_decisions": [item.to_dict() for item in self.project_decisions],
            "global_patterns": [item.to_dict() for item in self.global_patterns],
            "memory_events": [item.to_dict() for item in self.memory_events],
            "retention_policy": self.retention_policy.to_dict() if self.retention_policy else None,
            "revision_history": [item.to_dict() for item in self.revision_history],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryState":
        """Rehydrate memory state from serialized data."""

        retention_policy = payload.get("retention_policy")
        return cls(
            state_id=str(payload["state_id"]),
            state_version=int(payload.get("state_version", 1)),
            memory_items=tuple(
                MemoryItem.from_dict(item)
                for item in _ensure_collection(payload.get("memory_items", payload.get("items", ())), "memory_items")
            ),
            session_summaries=tuple(
                SessionSummary.from_dict(item)
                for item in _ensure_collection(payload.get("session_summaries", ()), "session_summaries")
            ),
            project_decisions=tuple(
                ProjectDecision.from_dict(item)
                for item in _ensure_collection(payload.get("project_decisions", ()), "project_decisions")
            ),
            global_patterns=tuple(
                GlobalPattern.from_dict(item)
                for item in _ensure_collection(payload.get("global_patterns", ()), "global_patterns")
            ),
            memory_events=tuple(
                MemoryEvent.from_dict(item)
                for item in _ensure_collection(payload.get("memory_events", ()), "memory_events")
            ),
            retention_policy=RetentionPolicy.from_dict(retention_policy) if retention_policy else None,
            revision_history=tuple(
                MemoryRevision.from_dict(item)
                for item in _ensure_collection(payload.get("revision_history", ()), "revision_history")
            ),
            created_at=datetime.fromisoformat(
                str(payload.get("created_at", datetime.fromtimestamp(0, UTC).isoformat()))
            ),
            updated_at=datetime.fromisoformat(
                str(payload.get("updated_at", datetime.fromtimestamp(0, UTC).isoformat()))
            ),
        )

    def append_memory_item(self, memory_item: MemoryItem) -> "MemoryState":
        """Append a memory item and record a revision."""

        if not isinstance(memory_item, MemoryItem):
            raise ValueError("memory_item must be a MemoryItem instance.")
        return self._advance(
            "memory item appended",
            memory_items=self.memory_items + (memory_item,),
        )

    def append_session_summary(self, session_summary: SessionSummary) -> "MemoryState":
        """Append a session summary and record a revision."""

        if not isinstance(session_summary, SessionSummary):
            raise ValueError("session_summary must be a SessionSummary instance.")
        return self._advance(
            "session summary appended",
            session_summaries=self.session_summaries + (session_summary,),
        )

    def append_project_decision(self, project_decision: ProjectDecision) -> "MemoryState":
        """Append a project decision and record a revision."""

        if not isinstance(project_decision, ProjectDecision):
            raise ValueError("project_decision must be a ProjectDecision instance.")
        return self._advance(
            "project decision appended",
            project_decisions=self.project_decisions + (project_decision,),
        )

    def append_global_pattern(self, global_pattern: GlobalPattern) -> "MemoryState":
        """Append a global pattern and record a revision."""

        if not isinstance(global_pattern, GlobalPattern):
            raise ValueError("global_pattern must be a GlobalPattern instance.")
        return self._advance(
            "global pattern appended",
            global_patterns=self.global_patterns + (global_pattern,),
        )

    def append_memory_event(self, memory_event: MemoryEvent) -> "MemoryState":
        """Append a memory event and record a revision."""

        if not isinstance(memory_event, MemoryEvent):
            raise ValueError("memory_event must be a MemoryEvent instance.")
        return self._advance(
            "memory event appended",
            memory_events=self.memory_events + (memory_event,),
        )

    def with_retention_policy(self, retention_policy: RetentionPolicy) -> "MemoryState":
        """Set the current retention policy and record a revision."""

        if not isinstance(retention_policy, RetentionPolicy):
            raise ValueError("retention_policy must be a RetentionPolicy instance.")
        return self._advance(
            "retention policy updated",
            retention_policy=retention_policy,
        )

    def record_revision(self, summary: str) -> "MemoryState":
        """Append a revision record without changing the state payload."""

        return self._bump(summary)

    def _bump(self, summary: str) -> "MemoryState":
        """Return a new state snapshot with an appended revision."""

        next_revision_number = self.state_version + 1
        revision = MemoryRevision(
            revision_id=f"{self.state_id}-rev-{next_revision_number:04d}",
            revision_number=next_revision_number,
            summary=summary,
        )
        return replace(
            self,
            state_version=next_revision_number,
            revision_history=self.revision_history + (revision,),
            updated_at=revision.created_at,
        )

    def _advance(
        self,
        summary: str,
        *,
        memory_items: tuple[MemoryItem, ...] | None = None,
        session_summaries: tuple[SessionSummary, ...] | None = None,
        project_decisions: tuple[ProjectDecision, ...] | None = None,
        global_patterns: tuple[GlobalPattern, ...] | None = None,
        memory_events: tuple[MemoryEvent, ...] | None = None,
        retention_policy: RetentionPolicy | None = None,
    ) -> "MemoryState":
        """Append a revision and apply the requested state updates."""

        next_state = self._bump(summary)
        updates: dict[str, Any] = {}
        if memory_items is not None:
            updates["memory_items"] = memory_items
        if session_summaries is not None:
            updates["session_summaries"] = session_summaries
        if project_decisions is not None:
            updates["project_decisions"] = project_decisions
        if global_patterns is not None:
            updates["global_patterns"] = global_patterns
        if memory_events is not None:
            updates["memory_events"] = memory_events
        if retention_policy is not None:
            updates["retention_policy"] = retention_policy
        return replace(next_state, **updates) if updates else next_state
