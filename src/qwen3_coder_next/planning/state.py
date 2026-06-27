"""Planner state container for Part 3 Step 1."""

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

from qwen3_coder_next.planning.schemas import (
    PLANNER_SCHEMA_VERSION,
    PlanArtifact,
    PlanGraph,
    PlannerRequest,
)


@dataclass(frozen=True, slots=True)
class PlannerRevision:
    """Immutable record of a planner state revision."""

    revision_id: str
    revision_number: int
    summary: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    schema_version: int = PLANNER_SCHEMA_VERSION

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
    def from_dict(cls, payload: dict[str, Any]) -> "PlannerRevision":
        """Rehydrate a revision from a serialized mapping."""

        return cls(
            revision_id=str(payload["revision_id"]),
            revision_number=int(payload["revision_number"]),
            summary=str(payload["summary"]),
            created_at=datetime.fromisoformat(str(payload.get("created_at", datetime.now(UTC).isoformat()))),
            schema_version=int(payload.get("schema_version", PLANNER_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class PlannerState:
    """Explicit, revisioned planner state container."""

    state_id: str
    state_version: int = 1
    current_request: PlannerRequest | None = None
    plan_draft: PlanGraph | None = None
    validated_plan: PlanArtifact | None = None
    assumptions: tuple[str, ...] = ()
    revision_history: tuple[PlannerRevision, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the planner state into a deterministic mapping."""

        return {
            "state_id": self.state_id,
            "state_version": self.state_version,
            "current_request": self.current_request.to_dict() if self.current_request else None,
            "plan_draft": self.plan_draft.to_dict() if self.plan_draft else None,
            "validated_plan": self.validated_plan.to_dict() if self.validated_plan else None,
            "assumptions": list(self.assumptions),
            "revision_history": [item.to_dict() for item in self.revision_history],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlannerState":
        """Rehydrate planner state from a serialized mapping."""

        current_request = payload.get("current_request")
        plan_draft = payload.get("plan_draft")
        validated_plan = payload.get("validated_plan")
        return cls(
            state_id=str(payload["state_id"]),
            state_version=int(payload.get("state_version", 1)),
            current_request=PlannerRequest.from_dict(current_request) if current_request else None,
            plan_draft=PlanGraph.from_dict(plan_draft) if plan_draft else None,
            validated_plan=PlanArtifact.from_dict(validated_plan) if validated_plan else None,
            assumptions=tuple(payload.get("assumptions", ())),
            revision_history=tuple(
                PlannerRevision.from_dict(item) for item in payload.get("revision_history", ())
            ),
            created_at=datetime.fromisoformat(str(payload.get("created_at", datetime.now(UTC).isoformat()))),
            updated_at=datetime.fromisoformat(str(payload.get("updated_at", datetime.now(UTC).isoformat()))),
        )

    def _bump(self, summary: str) -> "PlannerState":
        """Return a new state snapshot with an appended revision."""

        next_revision_number = self.state_version + 1
        revision = PlannerRevision(
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

    def with_current_request(self, request: PlannerRequest) -> "PlannerState":
        """Return a new planner state with the current request set."""

        return self._bump("current request updated")._replace_current_request(request)

    def with_plan_draft(self, plan_draft: PlanGraph) -> "PlannerState":
        """Return a new planner state with the plan draft set."""

        return self._bump("plan draft updated")._replace_plan_draft(plan_draft)

    def with_validated_plan(self, validated_plan: PlanArtifact) -> "PlannerState":
        """Return a new planner state with the validated plan set."""

        return self._bump("validated plan published")._replace_validated_plan(validated_plan)

    def add_assumption(self, assumption: str) -> "PlannerState":
        """Return a new planner state with an appended assumption."""

        return self._bump("assumption added")._replace_assumptions(self.assumptions + (assumption,))

    def record_revision(self, summary: str) -> "PlannerState":
        """Return a new planner state with a revision record only."""

        return self._bump(summary)

    def _replace_current_request(self, request: PlannerRequest | None) -> "PlannerState":
        return replace(self, current_request=request)

    def _replace_plan_draft(self, plan_draft: PlanGraph | None) -> "PlannerState":
        return replace(self, plan_draft=plan_draft)

    def _replace_validated_plan(self, validated_plan: PlanArtifact | None) -> "PlannerState":
        return replace(self, validated_plan=validated_plan)

    def _replace_assumptions(self, assumptions: tuple[str, ...]) -> "PlannerState":
        return replace(self, assumptions=assumptions)

