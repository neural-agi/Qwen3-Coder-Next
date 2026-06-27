"""Deterministic dependency resolution for Part 3 Step 4."""

from heapq import heappop, heappush
from dataclasses import dataclass

from qwen3_coder_next.planning.schemas import PlanDraft, PlanEdge, PlanGraph, PlanStep
from qwen3_coder_next.planning.state import PlannerState


class PlanningDependencyError(ValueError):
    """Base error for dependency resolution failures."""


class MalformedPlanDraftError(PlanningDependencyError):
    """Raised when dependency resolution receives an invalid plan draft."""


@dataclass(frozen=True, slots=True)
class DependencyResolver:
    """Resolve deterministic dependencies for a draft plan."""

    def resolve(self, draft: PlanDraft) -> PlanGraph:
        """Convert a plan draft into a dependency-aware plan graph."""

        if not isinstance(draft, PlanDraft):
            raise MalformedPlanDraftError("Dependency resolution requires a PlanDraft.")
        if not draft.steps:
            raise MalformedPlanDraftError("PlanDraft.steps must not be empty.")

        steps = tuple(draft.steps)
        step_by_id = {step.step_id: step for step in steps}
        adjacency: dict[str, set[str]] = {step.step_id: set() for step in steps}
        in_degree: dict[str, int] = {step.step_id: 0 for step in steps}
        edges: list[PlanEdge] = []

        for index, step in enumerate(steps):
            declared_dependencies = tuple(dep for dep in step.dependencies if dep)
            if declared_dependencies:
                for dependency_id in declared_dependencies:
                    if dependency_id not in step_by_id:
                        raise MalformedPlanDraftError(
                            f"Unknown dependency '{dependency_id}' in step '{step.step_id}'."
                        )
                    if step.step_id not in adjacency[dependency_id]:
                        adjacency[dependency_id].add(step.step_id)
                        in_degree[step.step_id] += 1
                        edges.append(
                            PlanEdge(
                                source_step_id=dependency_id,
                                target_step_id=step.step_id,
                            )
                        )
            elif index > 0:
                previous_step_id = steps[index - 1].step_id
                if step.step_id not in adjacency[previous_step_id]:
                    adjacency[previous_step_id].add(step.step_id)
                    in_degree[step.step_id] += 1
                    edges.append(
                        PlanEdge(
                            source_step_id=previous_step_id,
                            target_step_id=step.step_id,
                        )
                    )

        ordered_nodes = self._topological_order(steps, adjacency, in_degree)
        if len(ordered_nodes) != len(steps):
            raise MalformedPlanDraftError("PlanDraft contains a dependency cycle.")

        return PlanGraph(
            nodes=tuple(ordered_nodes),
            edges=tuple(edges),
            topological_order=tuple(step.step_id for step in ordered_nodes),
            critical_path=tuple(step.step_id for step in ordered_nodes),
        )

    def update_state(self, state: PlannerState, draft: PlanDraft) -> PlannerState:
        """Populate planner state with a resolved dependency graph."""

        return state.with_plan_draft(self.resolve(draft))

    def _topological_order(
        self,
        steps: tuple[PlanStep, ...],
        adjacency: dict[str, set[str]],
        in_degree: dict[str, int],
    ) -> list[PlanStep]:
        order_index = {step.step_id: index for index, step in enumerate(steps)}
        step_by_id = {step.step_id: step for step in steps}
        queue: list[tuple[int, str]] = []
        for step_id, degree in in_degree.items():
            if degree == 0:
                heappush(queue, (order_index[step_id], step_id))
        ordered_steps: list[PlanStep] = []
        remaining_in_degree = dict(in_degree)

        while queue:
            _, step_id = heappop(queue)
            ordered_steps.append(step_by_id[step_id])
            for target_id in sorted(adjacency[step_id], key=order_index.__getitem__):
                remaining_in_degree[target_id] -= 1
                if remaining_in_degree[target_id] == 0:
                    heappush(queue, (order_index[target_id], target_id))

        return ordered_steps
