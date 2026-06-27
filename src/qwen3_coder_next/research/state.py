"""Research state container for Part 4 Step 1."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

from qwen3_coder_next.research.schemas import (
    RESEARCH_SCHEMA_VERSION,
    EvidenceItem,
    ResearchPacket,
    ResearchRequest,
    ResearchStateStatus,
    SourceHandle,
    SourcePolicy,
)


@dataclass(frozen=True, slots=True)
class ResearchRevision:
    """Immutable record of a research state revision."""

    revision_id: str
    revision_number: int
    summary: str
    created_at: datetime = field(default_factory=lambda: datetime.fromtimestamp(0, UTC))
    schema_version: int = RESEARCH_SCHEMA_VERSION

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
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchRevision":
        """Rehydrate a revision from serialized data."""

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
            schema_version=int(payload.get("schema_version", RESEARCH_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class ResearchState:
    """Explicit, revisioned research state container."""

    state_id: str
    status: ResearchStateStatus = ResearchStateStatus.RECEIVED
    current_request: ResearchRequest | None = None
    source_policy: SourcePolicy | None = None
    selected_sources: tuple[SourceHandle, ...] = ()
    evidence_items: tuple[EvidenceItem, ...] = ()
    research_packet: ResearchPacket | None = None
    revision_history: tuple[ResearchRevision, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.fromtimestamp(0, UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.fromtimestamp(0, UTC))
    state_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize the research state into a deterministic mapping."""

        return {
            "state_id": self.state_id,
            "status": self.status.value,
            "current_request": self.current_request.to_dict() if self.current_request else None,
            "source_policy": self.source_policy.to_dict() if self.source_policy else None,
            "selected_sources": [item.to_dict() for item in self.selected_sources],
            "evidence_items": [item.to_dict() for item in self.evidence_items],
            "research_packet": self.research_packet.to_dict() if self.research_packet else None,
            "revision_history": [item.to_dict() for item in self.revision_history],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "state_version": self.state_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchState":
        """Rehydrate research state from serialized data."""

        current_request = payload.get("current_request")
        source_policy = payload.get("source_policy")
        research_packet = payload.get("research_packet")
        return cls(
            state_id=str(payload["state_id"]),
            status=ResearchStateStatus(str(payload.get("status", ResearchStateStatus.RECEIVED.value))),
            current_request=ResearchRequest.from_dict(current_request) if current_request else None,
            source_policy=SourcePolicy.from_dict(source_policy) if source_policy else None,
            selected_sources=tuple(
                SourceHandle.from_dict(item) for item in payload.get("selected_sources", ())
            ),
            evidence_items=tuple(
                EvidenceItem.from_dict(item) for item in payload.get("evidence_items", ())
            ),
            research_packet=ResearchPacket.from_dict(research_packet) if research_packet else None,
            revision_history=tuple(
                ResearchRevision.from_dict(item) for item in payload.get("revision_history", ())
            ),
            created_at=datetime.fromisoformat(
                str(payload.get("created_at", datetime.fromtimestamp(0, UTC).isoformat()))
            ),
            updated_at=datetime.fromisoformat(
                str(payload.get("updated_at", datetime.fromtimestamp(0, UTC).isoformat()))
            ),
            state_version=int(payload.get("state_version", 1)),
        )

    def with_request(self, request: ResearchRequest) -> "ResearchState":
        """Return a new state snapshot with the current request set."""

        return self._advance(
            "research request received",
            status=ResearchStateStatus.RECEIVED,
            current_request=request,
        )

    def with_source_policy(self, source_policy: SourcePolicy) -> "ResearchState":
        """Return a new state snapshot with the source policy set."""

        return self._advance(
            "source policy classified",
            status=ResearchStateStatus.CLASSIFIED,
            source_policy=source_policy,
        )

    def with_selected_sources(self, selected_sources: tuple[SourceHandle, ...]) -> "ResearchState":
        """Return a new state snapshot with selected sources set."""

        return self._advance(
            "sources selected",
            status=ResearchStateStatus.SOURCES_SELECTED,
            selected_sources=selected_sources,
        )

    def add_evidence_item(self, evidence_item: EvidenceItem) -> "ResearchState":
        """Return a new state snapshot with an appended evidence item."""

        return self._advance(
            "evidence gathered",
            status=ResearchStateStatus.EVIDENCE_GATHERED,
            evidence_items=self.evidence_items + (evidence_item,),
        )

    def with_research_packet(self, research_packet: ResearchPacket) -> "ResearchState":
        """Return a new state snapshot with the research packet set."""

        return self._advance(
            "research packet built",
            status=ResearchStateStatus.PACKET_BUILT,
            research_packet=research_packet,
        )

    def with_status(self, status: ResearchStateStatus) -> "ResearchState":
        """Return a new state snapshot with the status updated."""

        return self._advance("research status updated", status=status)

    def record_revision(self, summary: str) -> "ResearchState":
        """Return a new state snapshot with only a revision record appended."""

        return self._bump(summary)

    def _bump(self, summary: str) -> "ResearchState":
        """Return a new state snapshot with an appended revision."""

        next_revision_number = self.state_version + 1
        revision = ResearchRevision(
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
        status: ResearchStateStatus | None = None,
        current_request: ResearchRequest | None = None,
        source_policy: SourcePolicy | None = None,
        selected_sources: tuple[SourceHandle, ...] | None = None,
        evidence_items: tuple[EvidenceItem, ...] | None = None,
        research_packet: ResearchPacket | None = None,
    ) -> "ResearchState":
        """Append a revision and apply the requested state updates."""

        next_state = self._bump(summary)
        updates: dict[str, Any] = {}
        if status is not None:
            updates["status"] = status
        if current_request is not None:
            updates["current_request"] = current_request
        if source_policy is not None:
            updates["source_policy"] = source_policy
        if selected_sources is not None:
            updates["selected_sources"] = selected_sources
        if evidence_items is not None:
            updates["evidence_items"] = evidence_items
        if research_packet is not None:
            updates["research_packet"] = research_packet
        return replace(next_state, **updates) if updates else next_state
