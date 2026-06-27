"""Smoke tests for Part 3 Step 3 decomposition."""

import unittest

from qwen3_coder_next.planning import (
    DecompositionEngine,
    MalformedDecompositionRequestError,
    PlanDraft,
    PlanStep,
    PlanSubgoal,
    PlannerRequest,
    PlannerState,
    PlannerRequestNormalizer,
)


class PlanningStep3SmokeTest(unittest.TestCase):
    """Verify deterministic decomposition behavior."""

    def setUp(self) -> None:
        self.normalizer = PlannerRequestNormalizer()
        self.engine = DecompositionEngine()

    def test_successful_decomposition(self) -> None:
        """Decompose a normalized request into a structured draft."""

        request = self.normalizer.normalize(
            "Add feature flag support",
            constraints=["no database migration", "preserve UX"],
            source_context=["billing page", "current UI"],
        ).request

        draft = self.engine.decompose(request)

        self.assertIsInstance(draft, PlanDraft)
        self.assertEqual(draft.task_id, request.task_id)
        self.assertGreaterEqual(len(draft.steps), 3)

    def test_deterministic_decomposition(self) -> None:
        """Produce the same draft for the same normalized request."""

        request = self.normalizer.normalize(
            {"task_id": "task-123", "user_goal": "Plan billing flag", "constraints": ["local only"]},
        ).request

        first = self.engine.decompose(request)
        second = self.engine.decompose(request)

        self.assertEqual(first, second)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_structured_plan_draft_generation(self) -> None:
        """Generate structured subgoals and plan steps rather than prose."""

        request = PlannerRequest(task_id="task-structured", user_goal="Prepare structured plan")
        draft = self.engine.decompose(request)

        self.assertTrue(all(isinstance(item, PlanSubgoal) for item in draft.subgoals))
        self.assertTrue(all(isinstance(item, PlanStep) for item in draft.steps))
        self.assertEqual(draft.subgoals[0].title, "Clarify scope")
        self.assertEqual(draft.steps[0].title, "Capture task scope")

    def test_planner_state_integration(self) -> None:
        """Populate planner state with the current request and generated draft."""

        request = self.normalizer.normalize("Prepare decomposition state").request
        state = PlannerState(state_id="planner-state-step3")

        updated = self.engine.update_state(state, request)

        self.assertEqual(updated.current_request, request)
        self.assertIsInstance(updated.plan_draft, PlanDraft)
        self.assertEqual(updated.plan_draft.task_id, request.task_id)
        self.assertEqual(len(updated.revision_history), 2)

    def test_malformed_request_handling(self) -> None:
        """Reject malformed decomposition requests."""

        with self.assertRaises(MalformedDecompositionRequestError):
            self.engine.decompose("not-a-request")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main(verbosity=2)
