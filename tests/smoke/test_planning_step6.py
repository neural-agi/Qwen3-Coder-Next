"""Smoke tests for Part 3 Step 6 artifact serialization."""

import unittest

from qwen3_coder_next.planning import (
    DependencyResolver,
    PlanDraft,
    PlanEdge,
    PlanGraph,
    PlanStep,
    PlanValidator,
    PlannerRequest,
    PlannerRequestNormalizer,
    PlannerState,
    PlanningArtifactSerializer,
    MalformedPlanningSerializedDataError,
    ValidationReport,
    deserialize_plan_draft,
    deserialize_plan_graph,
    deserialize_planner_request,
    deserialize_planner_state,
    deserialize_validation_report,
    serialize_plan_draft,
    serialize_plan_graph,
    serialize_planner_request,
    serialize_planner_state,
    serialize_validation_report,
)


class PlanningStep6SmokeTest(unittest.TestCase):
    """Verify deterministic artifact serialization behavior."""

    def setUp(self) -> None:
        self.normalizer = PlannerRequestNormalizer()
        self.serializer = PlanningArtifactSerializer()
        self.resolver = DependencyResolver()
        self.validator = PlanValidator()

    def _validated_graph(self) -> tuple[PlannerRequest, PlanDraft, PlanGraph, ValidationReport]:
        request = self.normalizer.normalize(
            "Serialize planning artifacts",
            constraints=["local only"],
            source_context=["session notes"],
        ).request
        draft = PlanDraft(
            task_id=request.task_id,
            request=request,
            subgoals=(),
            steps=(
                PlanStep(step_id="step-1", title="Root"),
                PlanStep(step_id="step-2", title="Child", dependencies=("step-1",)),
            ),
        )
        graph = self.resolver.resolve(draft)
        report = self.validator.validate(graph)
        return request, draft, graph, report

    def test_serialization_and_deserialization(self) -> None:
        """Round-trip supported planning objects through canonical JSON."""

        request, draft, graph, report = self._validated_graph()
        state = PlannerState(state_id="planner-state-step6").with_current_request(request).with_plan_draft(graph)

        self.assertEqual(deserialize_planner_request(serialize_planner_request(request)), request)
        self.assertEqual(deserialize_plan_draft(serialize_plan_draft(draft)), draft)
        self.assertEqual(deserialize_plan_graph(serialize_plan_graph(graph)), graph)
        self.assertEqual(deserialize_validation_report(serialize_validation_report(report)), report)
        self.assertEqual(deserialize_planner_state(serialize_planner_state(state)), state)

    def test_deterministic_output(self) -> None:
        """Produce identical serialized output for equivalent objects."""

        request, draft, graph, report = self._validated_graph()

        self.assertEqual(serialize_planner_request(request), serialize_planner_request(request))
        self.assertEqual(serialize_plan_draft(draft), serialize_plan_draft(draft))
        self.assertEqual(serialize_plan_graph(graph), serialize_plan_graph(graph))
        self.assertEqual(serialize_validation_report(report), serialize_validation_report(report))

    def test_schema_version_compatibility(self) -> None:
        """Preserve schema versions through serialization and deserialization."""

        request, draft, graph, report = self._validated_graph()
        state = PlannerState(state_id="planner-state-step6", current_request=request, plan_draft=graph)

        self.assertEqual(deserialize_planner_request(request.to_dict()).schema_version, request.schema_version)
        self.assertEqual(deserialize_plan_draft(draft.to_dict()).schema_version, draft.schema_version)
        self.assertEqual(deserialize_plan_graph(graph.to_dict()).schema_version, graph.schema_version)
        self.assertEqual(deserialize_validation_report(report.to_dict()).schema_version, report.schema_version)
        self.assertEqual(deserialize_planner_state(state.to_dict()).state_version, state.state_version)

    def test_malformed_serialized_input(self) -> None:
        """Reject malformed serialized payloads."""

        with self.assertRaises(MalformedPlanningSerializedDataError):
            deserialize_planner_request("not-json")

        with self.assertRaises(MalformedPlanningSerializedDataError):
            deserialize_plan_graph({"nodes": "not-a-list"})  # type: ignore[arg-type]

    def test_backward_compatibility(self) -> None:
        """Continue accepting the existing dictionary payloads."""

        request, draft, graph, report = self._validated_graph()
        self.assertEqual(deserialize_planner_request(request.to_dict()), request)
        self.assertEqual(deserialize_plan_draft(draft.to_dict()), draft)
        self.assertEqual(deserialize_plan_graph(graph.to_dict()), graph)
        self.assertEqual(deserialize_validation_report(report.to_dict()), report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
