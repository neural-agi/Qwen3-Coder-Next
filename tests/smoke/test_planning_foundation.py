"""Smoke tests for the planning foundation."""

import unittest

from qwen3_coder_next.planning import (
    PlanRequest,
    PlanResult,
    PlanStatus,
    PlanStep,
    Planner,
    SimplePlanner,
)
from qwen3_coder_next.planning.schemas import PlanStep as SchemaPlanStep


class PlanningFoundationSmokeTest(unittest.TestCase):
    """Verify the planning foundation contracts and implementation."""

    def test_planning_contracts_can_be_created(self) -> None:
        """Create each planning contract type."""

        step = PlanStep(step_id="step-1", title="Review repository")
        request = PlanRequest(request_id="plan-1", objective="Add planning support")
        result = PlanResult(
            request_id="plan-1",
            status=PlanStatus.READY,
            summary="Plan ready",
            steps=(step,),
        )

        self.assertEqual(step.title, "Review repository")
        self.assertIs(PlanStep, SchemaPlanStep)
        self.assertEqual(request.objective, "Add planning support")
        self.assertEqual(result.status, PlanStatus.READY)

    def test_simple_planner_generates_a_minimal_plan(self) -> None:
        """Generate a deterministic plan from a request."""

        planner = SimplePlanner()
        result = planner.plan(
            PlanRequest(
                request_id="plan-2",
                objective="Prepare the next roadmap step",
            )
        )

        self.assertIsInstance(planner, Planner)
        self.assertEqual(result.request_id, "plan-2")
        self.assertEqual(result.status, PlanStatus.READY)
        self.assertEqual(len(result.steps), 2)
        self.assertEqual(result.steps[0].title, "Clarify objective")
        self.assertEqual(result.steps[1].title, "Prepare execution")
        self.assertEqual(result.steps[0].objective, "Prepare the next roadmap step")
        self.assertEqual(result.steps[1].dependencies, ("plan-2-step-1",))
