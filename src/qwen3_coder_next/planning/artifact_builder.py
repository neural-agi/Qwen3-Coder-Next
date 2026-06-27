"""Deterministic planning artifact builder for Part 3 Step 8."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from qwen3_coder_next.planning.schemas import (
    PLANNER_SCHEMA_VERSION,
    PlanArtifact,
    PlanEdge,
    PlanGraph,
    PlannerRequest,
    ValidationReport,
    ValidationStatus,
)


class PlanningArtifactBuildError(ValueError):
    """Base error for artifact building failures."""


class MalformedPlanningArtifactInputError(PlanningArtifactBuildError):
    """Raised when artifact building receives invalid validated planning output."""


@dataclass(frozen=True, slots=True)
class PlanArtifactBuilder:
    """Build deterministic planning artifacts from validated planning output."""

    def build(
        self,
        request: PlannerRequest,
        plan_graph: PlanGraph,
        validation_report: ValidationReport,
    ) -> PlanArtifact:
        """Build a stable planning artifact from validated planner output."""

        if not isinstance(request, PlannerRequest):
            raise MalformedPlanningArtifactInputError(
                "Artifact building requires a PlannerRequest."
            )
        if not isinstance(plan_graph, PlanGraph):
            raise MalformedPlanningArtifactInputError(
                "Artifact building requires a PlanGraph."
            )
        if not isinstance(validation_report, ValidationReport):
            raise MalformedPlanningArtifactInputError(
                "Artifact building requires a ValidationReport."
            )
        if validation_report.status not in {ValidationStatus.VALID, ValidationStatus.WARNING}:
            raise MalformedPlanningArtifactInputError(
                "Artifact building requires a validated or warning-level plan."
            )
        if not plan_graph.nodes:
            raise MalformedPlanningArtifactInputError(
                "PlanGraph.nodes must not be empty."
            )

        ordered_steps = tuple(plan_graph.nodes)
        dependency_map = self._build_dependency_map(plan_graph)
        request_summary = self._build_request_summary(request)
        risks = tuple(validation_report.blocking_errors)
        assumptions = tuple(request.constraints)
        handoff_notes = self._build_handoff_notes(validation_report)
        digest = self._build_digest(request, plan_graph, validation_report)

        return PlanArtifact(
            task_id=request.task_id,
            request_summary=request_summary,
            ordered_steps=ordered_steps,
            dependency_map=dependency_map,
            risks=risks,
            assumptions=assumptions,
            handoff_notes=handoff_notes,
            artifact_id=f"{request.task_id}-artifact-{digest[:12]}",
            revision_id=f"{request.task_id}-artifact-rev-{digest[12:20]}",
            schema_version=PLANNER_SCHEMA_VERSION,
        )

    def _build_dependency_map(self, plan_graph: PlanGraph) -> dict[str, tuple[str, ...]]:
        node_ids = {node.step_id for node in plan_graph.nodes}
        dependency_map: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
        for edge in plan_graph.edges:
            if not isinstance(edge, PlanEdge):
                continue
            if edge.target_step_id in dependency_map and edge.source_step_id in node_ids:
                dependency_map[edge.target_step_id].append(edge.source_step_id)
        return {
            step_id: tuple(sorted(dependencies))
            for step_id, dependencies in sorted(dependency_map.items())
        }

    def _build_request_summary(self, request: PlannerRequest) -> str:
        summary = request.user_goal.strip()
        return summary or request.task_id

    def _build_handoff_notes(self, validation_report: ValidationReport) -> str:
        if validation_report.warnings:
            return "Validated plan with warnings."
        return "Validated plan ready for downstream consumption."

    def _build_digest(
        self,
        request: PlannerRequest,
        plan_graph: PlanGraph,
        validation_report: ValidationReport,
    ) -> str:
        canonical_payload: dict[str, Any] = {
            "request": request.to_dict(),
            "graph": plan_graph.to_dict(),
            "report": validation_report.to_dict(),
            "schema_version": PLANNER_SCHEMA_VERSION,
        }
        canonical_json = json.dumps(
            canonical_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return sha256(canonical_json.encode("utf-8")).hexdigest()


def build_plan_artifact(
    request: PlannerRequest,
    plan_graph: PlanGraph,
    validation_report: ValidationReport,
) -> PlanArtifact:
    """Build a planning artifact using the default builder."""

    return PlanArtifactBuilder().build(request, plan_graph, validation_report)
