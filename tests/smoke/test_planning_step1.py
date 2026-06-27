"""Smoke tests for Part 3 Step 1 planning schemas and state."""

from datetime import UTC, datetime
import unittest

from qwen3_coder_next.planning import (
    CoverageMetrics,
    PlanArtifact,
    PlanEdge,
    PlanGraph,
    PlanStep,
    PlannerRequest,
    PlannerRevision,
    PlannerState,
    ValidationReport,
    ValidationStatus,
)


class PlanningStep1SmokeTest(unittest.TestCase):
    """Verify schema creation, serialization, and state updates."""

    def test_schema_creation_and_round_trip(self) -> None:
        """Create the core planning schemas and round-trip them through dict form."""

        request = PlannerRequest(
            task_id="task-042",
            user_goal="Add planning support",
            constraints=("no database", "local only"),
            environment={"repo": "Qwen3-Coder-Next", "branch": "feature/planning"},
            source_context=("session notes", "architecture docs"),
        )
        step = PlanStep(
            step_id="step-1",
            title="Define boundary",
            objective="Describe the planner contract",
            inputs=("requirements",),
            outputs=("schema",),
            dependencies=(),
            acceptance_criteria=("stable identifiers",),
            owner_hint="planner",
        )
        graph = PlanGraph(
            nodes=(step,),
            edges=(PlanEdge(source_step_id="step-1", target_step_id="step-1", relationship="self"),),
            topological_order=("step-1",),
            critical_path=("step-1",),
        )
        artifact = PlanArtifact(
            task_id="task-042",
            request_summary="Minimal planning handoff",
            ordered_steps=(step,),
            dependency_map={"step-1": ()},
            risks=("Scope drift",),
            assumptions=("No external research",),
            handoff_notes="Downstream agents should consume this artifact.",
            artifact_id="artifact-001",
            revision_id="task-042-rev-0001",
        )
        report = ValidationReport(
            status=ValidationStatus.VALID,
            blocking_errors=(),
            warnings=("None",),
            coverage_metrics=CoverageMetrics(total_steps=1, covered_steps=1),
            validated_at=datetime.now(UTC),
        )

        self.assertEqual(PlannerRequest.from_dict(request.to_dict()), request)
        self.assertEqual(PlanStep.from_dict(step.to_dict()), step)
        self.assertEqual(PlanGraph.from_dict(graph.to_dict()), graph)
        self.assertEqual(PlanArtifact.from_dict(artifact.to_dict()), artifact)
        self.assertEqual(ValidationReport.from_dict(report.to_dict()), report)

    def test_planner_state_creation_and_updates(self) -> None:
        """Create planner state and verify immutable update behavior."""

        request = PlannerRequest(task_id="task-100", user_goal="Plan work")
        step = PlanStep(step_id="step-100", title="Prepare", objective="Prepare plan")
        graph = PlanGraph(nodes=(step,), topological_order=("step-100",))
        artifact = PlanArtifact(
            task_id="task-100",
            request_summary="Plan summary",
            ordered_steps=(step,),
        )
        state = PlannerState(state_id="planner-state-001")

        updated = (
            state.with_current_request(request)
            .with_plan_draft(graph)
            .with_validated_plan(artifact)
            .add_assumption("No repository knowledge graph")
        )

        self.assertEqual(state.state_version, 1)
        self.assertEqual(updated.state_id, "planner-state-001")
        self.assertEqual(updated.current_request, request)
        self.assertEqual(updated.plan_draft, graph)
        self.assertEqual(updated.validated_plan, artifact)
        self.assertEqual(updated.assumptions, ("No repository knowledge graph",))
        self.assertEqual(len(updated.revision_history), 4)
        self.assertEqual(updated.revision_history[0].revision_id, "planner-state-001-rev-0002")
        self.assertEqual(updated.revision_history[-1].revision_number, 5)
        self.assertEqual(PlannerState.from_dict(updated.to_dict()), updated)


if __name__ == "__main__":
    unittest.main(verbosity=2)
