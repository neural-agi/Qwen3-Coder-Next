"""Planner schema definitions for Part 3 Step 1."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


PLANNER_SCHEMA_VERSION = 1


class ValidationStatus(StrEnum):
    """Supported validation outcome states."""

    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class PlannerRequest:
    """Normalized request boundary for planning."""

    task_id: str
    user_goal: str
    constraints: tuple[str, ...] = ()
    environment: dict[str, Any] = field(default_factory=dict)
    source_context: tuple[str, ...] = ()
    schema_version: int = PLANNER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the request into a deterministic mapping."""

        return {
            "task_id": self.task_id,
            "user_goal": self.user_goal,
            "constraints": list(self.constraints),
            "environment": dict(self.environment),
            "source_context": list(self.source_context),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlannerRequest":
        """Rehydrate a request from a serialized mapping."""

        return cls(
            task_id=str(payload["task_id"]),
            user_goal=str(payload["user_goal"]),
            constraints=tuple(payload.get("constraints", ())),
            environment=dict(payload.get("environment", {})),
            source_context=tuple(payload.get("source_context", ())),
            schema_version=int(payload.get("schema_version", PLANNER_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class PlanStep:
    """Single deterministic step within a planner output."""

    step_id: str
    title: str
    objective: str = ""
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    owner_hint: str = ""
    schema_version: int = PLANNER_SCHEMA_VERSION

    @property
    def description(self) -> str:
        """Compatibility alias for older planning code."""

        return self.objective

    @property
    def metadata(self) -> dict[str, Any]:
        """Compatibility alias for older planning code."""

        return {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize the plan step into a deterministic mapping."""

        return {
            "step_id": self.step_id,
            "title": self.title,
            "objective": self.objective,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "dependencies": list(self.dependencies),
            "acceptance_criteria": list(self.acceptance_criteria),
            "owner_hint": self.owner_hint,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlanStep":
        """Rehydrate a plan step from a serialized mapping."""

        return cls(
            step_id=str(payload["step_id"]),
            title=str(payload["title"]),
            objective=str(payload["objective"]),
            inputs=tuple(payload.get("inputs", ())),
            outputs=tuple(payload.get("outputs", ())),
            dependencies=tuple(payload.get("dependencies", ())),
            acceptance_criteria=tuple(payload.get("acceptance_criteria", ())),
            owner_hint=str(payload.get("owner_hint", "")),
            schema_version=int(payload.get("schema_version", PLANNER_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class PlanEdge:
    """Directed dependency edge between planner steps."""

    source_step_id: str
    target_step_id: str
    relationship: str = "depends_on"
    schema_version: int = PLANNER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the edge into a deterministic mapping."""

        return {
            "source_step_id": self.source_step_id,
            "target_step_id": self.target_step_id,
            "relationship": self.relationship,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlanEdge":
        """Rehydrate an edge from a serialized mapping."""

        return cls(
            source_step_id=str(payload["source_step_id"]),
            target_step_id=str(payload["target_step_id"]),
            relationship=str(payload.get("relationship", "depends_on")),
            schema_version=int(payload.get("schema_version", PLANNER_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class PlanGraph:
    """Directed acyclic graph representation of a plan."""

    nodes: tuple[PlanStep, ...]
    edges: tuple[PlanEdge, ...] = ()
    topological_order: tuple[str, ...] = ()
    critical_path: tuple[str, ...] = ()
    schema_version: int = PLANNER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the plan graph into a deterministic mapping."""

        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "topological_order": list(self.topological_order),
            "critical_path": list(self.critical_path),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlanGraph":
        """Rehydrate a plan graph from a serialized mapping."""

        return cls(
            nodes=tuple(PlanStep.from_dict(item) for item in payload.get("nodes", ())),
            edges=tuple(PlanEdge.from_dict(item) for item in payload.get("edges", ())),
            topological_order=tuple(payload.get("topological_order", ())),
            critical_path=tuple(payload.get("critical_path", ())),
            schema_version=int(payload.get("schema_version", PLANNER_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class PlanSubgoal:
    """Structured subgoal used during draft decomposition."""

    subgoal_id: str
    title: str
    objective: str
    notes: tuple[str, ...] = ()
    schema_version: int = PLANNER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the subgoal into a deterministic mapping."""

        return {
            "subgoal_id": self.subgoal_id,
            "title": self.title,
            "objective": self.objective,
            "notes": list(self.notes),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlanSubgoal":
        """Rehydrate a subgoal from a serialized mapping."""

        return cls(
            subgoal_id=str(payload["subgoal_id"]),
            title=str(payload["title"]),
            objective=str(payload["objective"]),
            notes=tuple(payload.get("notes", ())),
            schema_version=int(payload.get("schema_version", PLANNER_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class PlanDraft:
    """Draft plan produced by deterministic decomposition."""

    task_id: str
    request: PlannerRequest
    subgoals: tuple[PlanSubgoal, ...]
    steps: tuple[PlanStep, ...]
    notes: tuple[str, ...] = ()
    draft_version: int = 1
    schema_version: int = PLANNER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the draft into a deterministic mapping."""

        return {
            "task_id": self.task_id,
            "request": self.request.to_dict(),
            "subgoals": [subgoal.to_dict() for subgoal in self.subgoals],
            "steps": [step.to_dict() for step in self.steps],
            "notes": list(self.notes),
            "draft_version": self.draft_version,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlanDraft":
        """Rehydrate a draft from a serialized mapping."""

        return cls(
            task_id=str(payload["task_id"]),
            request=PlannerRequest.from_dict(dict(payload["request"])),
            subgoals=tuple(
                PlanSubgoal.from_dict(item) for item in payload.get("subgoals", ())
            ),
            steps=tuple(PlanStep.from_dict(item) for item in payload.get("steps", ())),
            notes=tuple(payload.get("notes", ())),
            draft_version=int(payload.get("draft_version", 1)),
            schema_version=int(payload.get("schema_version", PLANNER_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class PlanArtifact:
    """Stable handoff artifact produced from a validated plan."""

    task_id: str
    request_summary: str
    ordered_steps: tuple[PlanStep, ...]
    dependency_map: dict[str, tuple[str, ...]] = field(default_factory=dict)
    risks: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    handoff_notes: str = ""
    artifact_id: str = ""
    revision_id: str = ""
    schema_version: int = PLANNER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the artifact into a deterministic mapping."""

        return {
            "task_id": self.task_id,
            "request_summary": self.request_summary,
            "ordered_steps": [step.to_dict() for step in self.ordered_steps],
            "dependency_map": {
                key: list(value) for key, value in self.dependency_map.items()
            },
            "risks": list(self.risks),
            "assumptions": list(self.assumptions),
            "handoff_notes": self.handoff_notes,
            "artifact_id": self.artifact_id,
            "revision_id": self.revision_id,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlanArtifact":
        """Rehydrate a plan artifact from a serialized mapping."""

        return cls(
            task_id=str(payload["task_id"]),
            request_summary=str(payload["request_summary"]),
            ordered_steps=tuple(PlanStep.from_dict(item) for item in payload.get("ordered_steps", ())),
            dependency_map={
                key: tuple(value)
                for key, value in dict(payload.get("dependency_map", {})).items()
            },
            risks=tuple(payload.get("risks", ())),
            assumptions=tuple(payload.get("assumptions", ())),
            handoff_notes=str(payload.get("handoff_notes", "")),
            artifact_id=str(payload.get("artifact_id", "")),
            revision_id=str(payload.get("revision_id", "")),
            schema_version=int(payload.get("schema_version", PLANNER_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class CoverageMetrics:
    """Basic machine-readable validation coverage information."""

    total_steps: int
    covered_steps: int
    missing_inputs: tuple[str, ...] = ()
    missing_outputs: tuple[str, ...] = ()
    schema_version: int = PLANNER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize coverage data into a deterministic mapping."""

        return {
            "total_steps": self.total_steps,
            "covered_steps": self.covered_steps,
            "missing_inputs": list(self.missing_inputs),
            "missing_outputs": list(self.missing_outputs),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CoverageMetrics":
        """Rehydrate coverage metrics from a serialized mapping."""

        return cls(
            total_steps=int(payload["total_steps"]),
            covered_steps=int(payload["covered_steps"]),
            missing_inputs=tuple(payload.get("missing_inputs", ())),
            missing_outputs=tuple(payload.get("missing_outputs", ())),
            schema_version=int(payload.get("schema_version", PLANNER_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Machine-readable validation output for planner state."""

    status: ValidationStatus
    blocking_errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    coverage_metrics: CoverageMetrics = field(
        default_factory=lambda: CoverageMetrics(total_steps=0, covered_steps=0)
    )
    validated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    schema_version: int = PLANNER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the validation report into a deterministic mapping."""

        return {
            "status": self.status.value,
            "blocking_errors": list(self.blocking_errors),
            "warnings": list(self.warnings),
            "coverage_metrics": self.coverage_metrics.to_dict(),
            "validated_at": self.validated_at.isoformat(),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ValidationReport":
        """Rehydrate a validation report from a serialized mapping."""

        return cls(
            status=ValidationStatus(str(payload["status"])),
            blocking_errors=tuple(payload.get("blocking_errors", ())),
            warnings=tuple(payload.get("warnings", ())),
            coverage_metrics=CoverageMetrics.from_dict(payload.get("coverage_metrics", {})),
            validated_at=datetime.fromisoformat(str(payload.get("validated_at", datetime.now(UTC).isoformat()))),
            schema_version=int(payload.get("schema_version", PLANNER_SCHEMA_VERSION)),
        )
