"""Smoke tests for Part 3 Step 4 dependency resolution."""

import unittest

from qwen3_coder_next.planning import (
    DependencyResolver,
    MalformedPlanDraftError,
    PlanDraft,
    PlanGraph,
    PlanStep,
    PlannerRequest,
    PlannerRequestNormalizer,
    PlannerState,
)


class PlanningStep4SmokeTest(unittest.TestCase):
    """Verify deterministic dependency graph generation."""

    def setUp(self) -> None:
        self.normalizer = PlannerRequestNormalizer()
        self.resolver = DependencyResolver()

    def test_dependency_graph_creation(self) -> None:
        """Resolve a draft into a dependency-aware plan graph."""

        request = self.normalizer.normalize(
            "Build a planning graph",
            constraints=["local only"],
            source_context=["planning docs"],
        ).request
        draft = PlanDraft(
            task_id=request.task_id,
            request=request,
            subgoals=(),
            steps=(
                PlanStep(step_id="step-1", title="Prepare scope"),
                PlanStep(step_id="step-2", title="Assemble draft"),
                PlanStep(step_id="step-3", title="Finalize graph"),
            ),
        )

        graph = self.resolver.resolve(draft)

        self.assertIsInstance(graph, PlanGraph)
        self.assertEqual(graph.topological_order, ("step-1", "step-2", "step-3"))
        self.assertEqual(
            [(edge.source_step_id, edge.target_step_id) for edge in graph.edges],
            [("step-1", "step-2"), ("step-2", "step-3")],
        )

    def test_deterministic_graph_generation(self) -> None:
        """Return the same graph for the same draft."""

        request = self.normalizer.normalize("Deterministic graph").request
        draft = PlanDraft(
            task_id=request.task_id,
            request=request,
            subgoals=(),
            steps=(
                PlanStep(step_id="step-a", title="First"),
                PlanStep(step_id="step-b", title="Second"),
            ),
        )

        first = self.resolver.resolve(draft)
        second = self.resolver.resolve(draft)

        self.assertEqual(first, second)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_topological_ordering(self) -> None:
        """Honor declared dependencies while preserving stable ordering."""

        request = PlannerRequest(task_id="task-order", user_goal="Order graph")
        draft = PlanDraft(
            task_id=request.task_id,
            request=request,
            subgoals=(),
            steps=(
                PlanStep(step_id="step-root", title="Root"),
                PlanStep(
                    step_id="step-dependent",
                    title="Dependent",
                    dependencies=("step-root",),
                ),
                PlanStep(step_id="step-final", title="Final"),
            ),
        )

        graph = self.resolver.resolve(draft)

        self.assertEqual(graph.topological_order, ("step-root", "step-dependent", "step-final"))

    def test_planner_state_integration(self) -> None:
        """Populate planner state with the resolved graph."""

        request = self.normalizer.normalize("Integrate dependency state").request
        draft = PlanDraft(
            task_id=request.task_id,
            request=request,
            subgoals=(),
            steps=(
                PlanStep(step_id="step-1", title="One"),
                PlanStep(step_id="step-2", title="Two"),
            ),
        )
        state = PlannerState(state_id="planner-state-step4")

        updated = self.resolver.update_state(state, draft)

        self.assertEqual(updated.plan_draft, self.resolver.resolve(draft))

    def test_malformed_draft_handling(self) -> None:
        """Reject invalid drafts and unknown dependencies."""

        with self.assertRaises(MalformedPlanDraftError):
            self.resolver.resolve("not-a-draft")  # type: ignore[arg-type]

        request = PlannerRequest(task_id="task-bad", user_goal="Bad dependency")
        draft = PlanDraft(
            task_id=request.task_id,
            request=request,
            subgoals=(),
            steps=(
                PlanStep(step_id="step-1", title="One", dependencies=("missing",)),
            ),
        )
        with self.assertRaises(MalformedPlanDraftError):
            self.resolver.resolve(draft)

    def test_serialization_compatibility(self) -> None:
        """Round-trip the resolved graph through serialization."""

        request = self.normalizer.normalize("Serialize dependency graph").request
        draft = PlanDraft(
            task_id=request.task_id,
            request=request,
            subgoals=(),
            steps=(
                PlanStep(step_id="step-1", title="One"),
                PlanStep(step_id="step-2", title="Two"),
            ),
        )

        graph = self.resolver.resolve(draft)

        self.assertEqual(graph, PlanGraph.from_dict(graph.to_dict()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
