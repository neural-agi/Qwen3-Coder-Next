"""Deterministic plan validation for Part 3 Step 5."""

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime

from qwen3_coder_next.planning.schemas import (
    CoverageMetrics,
    PLANNER_SCHEMA_VERSION,
    PlanEdge,
    PlanGraph,
    PlanStep,
    ValidationReport,
    ValidationStatus,
)


class PlanningValidationError(ValueError):
    """Base error for plan validation failures."""


class MalformedPlanGraphError(PlanningValidationError):
    """Raised when validation receives an invalid plan graph object."""


_DETERMINISTIC_VALIDATED_AT = datetime.fromtimestamp(0, UTC)


@dataclass(frozen=True, slots=True)
class PlanValidator:
    """Perform deterministic structural validation for a resolved plan graph."""

    def validate(self, plan_graph: PlanGraph) -> ValidationReport:
        """Validate a resolved plan graph without mutating it."""

        if not isinstance(plan_graph, PlanGraph):
            raise MalformedPlanGraphError("Validation requires a PlanGraph instance.")

        blocking_errors: list[str] = []
        warnings: list[str] = []

        self._validate_nodes(plan_graph.nodes, blocking_errors)
        self._validate_edges(plan_graph.nodes, plan_graph.edges, blocking_errors)
        self._validate_topological_order(
            plan_graph.nodes,
            plan_graph.edges,
            plan_graph.topological_order,
            blocking_errors,
        )
        self._validate_critical_path(plan_graph.critical_path, plan_graph.nodes, blocking_errors)
        reachable_nodes = (
            self._reachable_nodes(
                plan_graph.nodes,
                plan_graph.edges,
                plan_graph.topological_order[0] if plan_graph.topological_order else None,
            )
            if not blocking_errors
            else set()
        )
        unreachable_nodes = self._missing_reachable_nodes(plan_graph.nodes, reachable_nodes)
        if unreachable_nodes:
            blocking_errors.append(
                "Unreachable nodes detected: " + ", ".join(unreachable_nodes)
            )

        total_steps = len(plan_graph.nodes)
        covered_steps = len(reachable_nodes) if reachable_nodes else total_steps - len(unreachable_nodes)
        if total_steps == 0:
            covered_steps = 0

        status = ValidationStatus.VALID if not blocking_errors else ValidationStatus.INVALID
        if warnings and status == ValidationStatus.VALID:
            status = ValidationStatus.WARNING

        metrics = CoverageMetrics(
            total_steps=total_steps,
            covered_steps=covered_steps,
        )
        return ValidationReport(
            status=status,
            blocking_errors=tuple(blocking_errors),
            warnings=tuple(warnings),
            coverage_metrics=metrics,
            validated_at=_DETERMINISTIC_VALIDATED_AT,
            schema_version=PLANNER_SCHEMA_VERSION,
        )

    def _validate_nodes(self, nodes: tuple[PlanStep, ...], blocking_errors: list[str]) -> set[str]:
        node_ids: list[str] = []
        for index, node in enumerate(nodes):
            if not isinstance(node, PlanStep):
                blocking_errors.append(f"Node at index {index} is not a PlanStep.")
                continue
            if not node.step_id or not node.title:
                blocking_errors.append(f"Node at index {index} is missing required fields.")
            node_ids.append(node.step_id)

        duplicates = self._duplicates(node_ids)
        if duplicates:
            blocking_errors.append(
                "Duplicate node identifiers detected: " + ", ".join(duplicates)
            )
        return set(node_ids)

    def _validate_edges(
        self,
        nodes: tuple[PlanStep, ...],
        edges: tuple[PlanEdge, ...],
        blocking_errors: list[str],
    ) -> None:
        node_ids = {node.step_id for node in nodes if isinstance(node, PlanStep)}
        seen_edges: set[tuple[str, str, str]] = set()
        for index, edge in enumerate(edges):
            if not isinstance(edge, PlanEdge):
                blocking_errors.append(f"Edge at index {index} is not a PlanEdge.")
                continue
            edge_key = (edge.source_step_id, edge.target_step_id, edge.relationship)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            if edge.source_step_id not in node_ids or edge.target_step_id not in node_ids:
                blocking_errors.append(
                    f"Edge at index {index} references missing nodes: "
                    f"{edge.source_step_id} -> {edge.target_step_id}."
                )
            if edge.source_step_id == edge.target_step_id:
                blocking_errors.append(
                    f"Edge at index {index} forms a self-reference on {edge.source_step_id}."
                )

    def _validate_topological_order(
        self,
        nodes: tuple[PlanStep, ...],
        edges: tuple[PlanEdge, ...],
        topological_order: tuple[str, ...],
        blocking_errors: list[str],
    ) -> None:
        node_ids = [node.step_id for node in nodes if isinstance(node, PlanStep)]
        if not topological_order:
            blocking_errors.append("Topological order must not be empty.")
            return
        if len(topological_order) != len(node_ids):
            blocking_errors.append("Topological order length does not match node count.")
        if self._duplicates(list(topological_order)):
            blocking_errors.append("Topological order contains duplicate identifiers.")
        if set(topological_order) != set(node_ids):
            blocking_errors.append("Topological order must reference every node exactly once.")

        order_index = {step_id: index for index, step_id in enumerate(topological_order)}
        for edge in edges:
            if not isinstance(edge, PlanEdge):
                continue
            if edge.source_step_id in order_index and edge.target_step_id in order_index:
                if order_index[edge.source_step_id] >= order_index[edge.target_step_id]:
                    blocking_errors.append(
                        "Topological order is inconsistent with dependency edges."
                    )
                    break

    def _validate_critical_path(
        self,
        critical_path: tuple[str, ...],
        nodes: tuple[PlanStep, ...],
        blocking_errors: list[str],
    ) -> None:
        if not critical_path:
            return
        node_ids = {node.step_id for node in nodes if isinstance(node, PlanStep)}
        missing = tuple(step_id for step_id in critical_path if step_id not in node_ids)
        if missing:
            blocking_errors.append(
                "Critical path references missing nodes: " + ", ".join(missing)
            )

    def _reachable_nodes(
        self,
        nodes: tuple[PlanStep, ...],
        edges: tuple[PlanEdge, ...],
        start_node_id: str | None,
    ) -> set[str]:
        node_ids = [node.step_id for node in nodes if isinstance(node, PlanStep)]
        adjacency: dict[str, set[str]] = defaultdict(set)

        for edge in edges:
            if not isinstance(edge, PlanEdge):
                continue
            if edge.source_step_id in node_ids and edge.target_step_id in node_ids:
                adjacency[edge.source_step_id].add(edge.target_step_id)

        if start_node_id is None or start_node_id not in node_ids:
            return set()

        queue = deque([start_node_id])
        reachable: set[str] = set()
        while queue:
            step_id = queue.popleft()
            if step_id in reachable:
                continue
            reachable.add(step_id)
            for target_id in sorted(adjacency.get(step_id, ())):
                if target_id not in reachable:
                    queue.append(target_id)
        return reachable

    def _missing_reachable_nodes(
        self,
        nodes: tuple[PlanStep, ...],
        reachable_nodes: set[str],
    ) -> tuple[str, ...]:
        node_ids = [node.step_id for node in nodes if isinstance(node, PlanStep)]
        missing = [step_id for step_id in node_ids if step_id not in reachable_nodes]
        return tuple(sorted(missing))

    def _duplicates(self, values: list[str]) -> tuple[str, ...]:
        seen: set[str] = set()
        duplicates: list[str] = []
        for value in values:
            if value in seen and value not in duplicates:
                duplicates.append(value)
            seen.add(value)
        return tuple(sorted(duplicates))


def validate_plan_graph(plan_graph: PlanGraph) -> ValidationReport:
    """Validate a plan graph using the default validator."""

    return PlanValidator().validate(plan_graph)
