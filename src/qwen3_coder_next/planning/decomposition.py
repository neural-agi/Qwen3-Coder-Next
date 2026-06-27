"""Deterministic decomposition engine for Part 3 Step 3."""

from dataclasses import dataclass

from qwen3_coder_next.planning.schemas import PlanDraft, PlanStep, PlanSubgoal, PlannerRequest
from qwen3_coder_next.planning.state import PlannerState


class PlanningDecompositionError(ValueError):
    """Base error for planning decomposition failures."""


class MalformedDecompositionRequestError(PlanningDecompositionError):
    """Raised when decomposition receives an invalid normalized request."""


@dataclass(frozen=True, slots=True)
class DecompositionEngine:
    """Deterministically decompose a normalized planner request into a plan draft."""

    def decompose(self, request: PlannerRequest) -> PlanDraft:
        """Build a deterministic draft plan from a normalized planner request."""

        if not isinstance(request, PlannerRequest):
            raise MalformedDecompositionRequestError(
                "Decomposition requires a normalized PlannerRequest."
            )
        if not request.user_goal.strip():
            raise MalformedDecompositionRequestError(
                "PlannerRequest.user_goal must not be empty."
            )

        subgoals: list[PlanSubgoal] = [
            PlanSubgoal(
                subgoal_id=f"{request.task_id}-subgoal-1",
                title="Clarify scope",
                objective=request.user_goal,
                notes=("Capture the task boundary from the normalized request.",),
            )
        ]

        steps: list[PlanStep] = [
            PlanStep(
                step_id=f"{request.task_id}-step-1",
                title="Capture task scope",
                objective=request.user_goal,
                inputs=("normalized request",),
                outputs=("task scope",),
                acceptance_criteria=("task scope is explicit",),
                owner_hint="planner",
            )
        ]

        if request.constraints:
            subgoals.append(
                PlanSubgoal(
                    subgoal_id=f"{request.task_id}-subgoal-{len(subgoals) + 1}",
                    title="Normalize constraints",
                    objective="Represent all hard constraints explicitly for later planning.",
                    notes=request.constraints,
                )
            )
            steps.append(
                PlanStep(
                    step_id=f"{request.task_id}-step-{len(steps) + 1}",
                    title="Record constraints",
                    objective="Translate request constraints into explicit planning boundaries.",
                    inputs=("constraints",),
                    outputs=("constraint boundary list",),
                    acceptance_criteria=("constraints are represented explicitly",),
                    owner_hint="planner",
                )
            )

        if request.source_context:
            subgoals.append(
                PlanSubgoal(
                    subgoal_id=f"{request.task_id}-subgoal-{len(subgoals) + 1}",
                    title="Capture source context",
                    objective="Preserve relevant context for later decomposition and validation.",
                    notes=request.source_context,
                )
            )
            steps.append(
                PlanStep(
                    step_id=f"{request.task_id}-step-{len(steps) + 1}",
                    title="Record source context",
                    objective="Represent contextual inputs that later planner stages may rely on.",
                    inputs=("source context",),
                    outputs=("context summary",),
                    acceptance_criteria=("source context is preserved",),
                    owner_hint="planner",
                )
            )

        steps.append(
            PlanStep(
                step_id=f"{request.task_id}-step-{len(steps) + 1}",
                title="Prepare execution-oriented draft",
                objective="Organize the normalized request into candidate work items for later ordering.",
                inputs=("task scope", "constraints", "source context"),
                outputs=("candidate step draft",),
                acceptance_criteria=("candidate work items are organized",),
                owner_hint="planner",
            )
        )

        notes = (
            "Deterministic decomposition draft.",
            f"Subgoal count: {len(subgoals)}",
            f"Step count: {len(steps)}",
        )
        return PlanDraft(
            task_id=request.task_id,
            request=request,
            subgoals=tuple(subgoals),
            steps=tuple(steps),
            notes=notes,
        )

    def update_state(self, state: PlannerState, request: PlannerRequest) -> PlannerState:
        """Populate planner state with a newly decomposed draft."""

        draft = self.decompose(request)
        next_state = state
        if next_state.current_request != request:
            next_state = next_state.with_current_request(request)
        return next_state.with_plan_draft(draft)
