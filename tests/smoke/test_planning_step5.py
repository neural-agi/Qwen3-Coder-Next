"""Smoke tests for Part 3 Step 5 plan validation."""

import unittest

from qwen3_coder_next.planning import (
    MalformedPlanGraphError,
    PlanDraft,
    PlanEdge,
    PlanGraph,
    PlanStep,
    PlanValidator,
    PlannerRequest,
    PlannerRequestNormalizer,
    ValidationReport,
    ValidationStatus,
    validate_plan_graph,
)


class PlanningStep5SmokeTest(unittest.TestCase):
    """Verify deterministic structural validation behavior."""

    def setUp(self) -> None:
        self.normalizer = PlannerRequestNormalizer()
        self.validator = PlanValidator()

    def _valid_graph(self) -> PlanGraph:
        request = self.normalizer.normalize("Validate graph").request
        draft = PlanDraft(
            task_id=request.task_id,
            request=request,
            subgoals=(),
            steps=(
                PlanStep(step_id="step-1", title="Root"),
                PlanStep(step_id="step-2", title="Child", dependencies=("step-1",)),
            ),
        )
        return PlanGraph(
            nodes=draft.steps,
            edges=(PlanEdge(source_step_id="step-1", target_step_id="step-2"),),
            topological_order=("step-1", "step-2"),
            critical_path=("step-1", "step-2"),
        )

    def test_valid_graph(self) -> None:
        """Validate a structurally correct plan graph."""

        report = self.validator.validate(self._valid_graph())

        self.assertIsInstance(report, ValidationReport)
        self.assertEqual(report.status, ValidationStatus.VALID)
        self.assertEqual(report.blocking_errors, ())
        self.assertEqual(report.coverage_metrics.total_steps, 2)
        self.assertEqual(report.coverage_metrics.covered_steps, 2)

    def test_empty_graph(self) -> None:
        """Reject an empty plan graph."""

        graph = PlanGraph(nodes=(), edges=(), topological_order=(), critical_path=())
        report = self.validator.validate(graph)

        self.assertEqual(report.status, ValidationStatus.INVALID)
        self.assertIn("Topological order must not be empty.", report.blocking_errors)

    def test_duplicate_identifiers(self) -> None:
        """Reject duplicate node identifiers."""

        graph = PlanGraph(
            nodes=(
                PlanStep(step_id="step-1", title="One"),
                PlanStep(step_id="step-1", title="Duplicate"),
            ),
            edges=(),
            topological_order=("step-1", "step-1"),
            critical_path=("step-1",),
        )

        report = self.validator.validate(graph)

        self.assertEqual(report.status, ValidationStatus.INVALID)
        self.assertIn("Duplicate node identifiers detected: step-1", report.blocking_errors)

    def test_invalid_dependency_references(self) -> None:
        """Reject edges that reference missing nodes."""

        graph = PlanGraph(
            nodes=(
                PlanStep(step_id="step-1", title="One"),
                PlanStep(step_id="step-2", title="Two"),
            ),
            edges=(PlanEdge(source_step_id="step-1", target_step_id="step-3"),),
            topological_order=("step-1", "step-2"),
            critical_path=("step-1",),
        )

        report = self.validator.validate(graph)

        self.assertEqual(report.status, ValidationStatus.INVALID)
        self.assertTrue(
            any("references missing nodes" in error for error in report.blocking_errors)
        )

    def test_unreachable_nodes(self) -> None:
        """Reject nodes that are not connected to the resolved graph."""

        graph = PlanGraph(
            nodes=(
                PlanStep(step_id="step-1", title="One"),
                PlanStep(step_id="step-2", title="Two"),
                PlanStep(step_id="step-3", title="Three"),
            ),
            edges=(PlanEdge(source_step_id="step-1", target_step_id="step-2"),),
            topological_order=("step-1", "step-2", "step-3"),
            critical_path=("step-1", "step-2"),
        )

        report = self.validator.validate(graph)

        self.assertEqual(report.status, ValidationStatus.INVALID)
        self.assertIn("Unreachable nodes detected: step-3", report.blocking_errors)

    def test_malformed_graphs(self) -> None:
        """Reject malformed graph objects and malformed graph members."""

        with self.assertRaises(MalformedPlanGraphError):
            self.validator.validate("not-a-graph")  # type: ignore[arg-type]

        malformed_graph = PlanGraph(
            nodes=("bad-node",),  # type: ignore[arg-type]
            edges=("bad-edge",),  # type: ignore[arg-type]
            topological_order=("bad-node",),
            critical_path=("bad-node",),
        )
        report = self.validator.validate(malformed_graph)

        self.assertEqual(report.status, ValidationStatus.INVALID)
        self.assertTrue(any("not a PlanStep" in error for error in report.blocking_errors))
        self.assertTrue(any("not a PlanEdge" in error for error in report.blocking_errors))

    def test_deterministic_validation(self) -> None:
        """Return the same report for the same graph."""

        graph = self._valid_graph()
        first = self.validator.validate(graph)
        second = validate_plan_graph(graph)

        self.assertEqual(first, second)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_validation_report_serialization(self) -> None:
        """Round-trip a validation report through dict serialization."""

        report = self.validator.validate(self._valid_graph())

        self.assertEqual(report, ValidationReport.from_dict(report.to_dict()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
