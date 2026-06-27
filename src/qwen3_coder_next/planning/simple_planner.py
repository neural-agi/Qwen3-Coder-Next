"""Initial planning implementation for the foundation layer."""

from qwen3_coder_next.planning.contracts import (
    PlanRequest,
    PlanResult,
    PlanStatus,
    PlanStep,
)
from qwen3_coder_next.planning.planner import Planner


class SimplePlanner(Planner):
    """Generate a minimal, deterministic plan from a request."""

    def plan(self, request: PlanRequest) -> PlanResult:
        """Return a small plan that prepares execution without agent logic."""

        steps = (
            PlanStep(
                step_id=f"{request.request_id}-step-1",
                title="Clarify objective",
                objective=request.objective,
                inputs=("planning request",),
                outputs=("clarified objective",),
                acceptance_criteria=("objective is captured",),
                owner_hint="simple-planner",
            ),
            PlanStep(
                step_id=f"{request.request_id}-step-2",
                title="Prepare execution",
                objective="Convert the objective into a ready-to-execute task.",
                inputs=("clarified objective",),
                outputs=("execution preparation",),
                dependencies=(f"{request.request_id}-step-1",),
                acceptance_criteria=("execution preparation is described",),
                owner_hint="simple-planner",
            ),
        )
        return PlanResult(
            request_id=request.request_id,
            status=PlanStatus.READY,
            summary=f"Prepared a minimal plan for: {request.objective}",
            steps=steps,
            metadata={"planner": "simple-planner"},
        )
