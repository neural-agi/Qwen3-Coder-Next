"""Smoke tests for Part 3 Step 8 artifact building."""

import unittest

from qwen3_coder_next.planning import (
    DependencyResolver,
    MalformedPlanningArtifactInputError,
    PlanArtifact,
    PlanArtifactBuilder,
    PlanDraft,
    PlanStep,
    PlannerRequest,
    PlannerRequestNormalizer,
    PlanValidator,
    ValidationStatus,
    build_plan_artifact,
    deserialize_plan_artifact,
    deserialize_plan_graph,
    serialize_plan_graph,
    serialize_plan_artifact,
)


class PlanningStep8SmokeTest(unittest.TestCase):
    """Verify deterministic artifact construction behavior."""

    def setUp(self) -> None:
        self.normalizer = PlannerRequestNormalizer()
        self.builder = PlanArtifactBuilder()
        self.resolver = DependencyResolver()
        self.validator = PlanValidator()

    def _validated_output(self) -> tuple[PlannerRequest, PlanDraft, PlanArtifact]:
        request = self.normalizer.normalize(
            "Build a planning artifact",
            constraints=["local only"],
            source_context=["runtime integration"],
        ).request
        draft = PlanDraft(
            task_id=request.task_id,
            request=request,
            subgoals=(),
            steps=(
                PlanStep(step_id="step-1", title="One"),
                PlanStep(step_id="step-2", title="Two", dependencies=("step-1",)),
            ),
        )
        graph = self.resolver.resolve(draft)
        report = self.validator.validate(graph)
        artifact = self.builder.build(request, graph, report)
        return request, draft, artifact

    def test_artifact_construction(self) -> None:
        """Construct a deterministic planning artifact from validated output."""

        request, _, artifact = self._validated_output()

        self.assertIsInstance(artifact, PlanArtifact)
        self.assertEqual(artifact.task_id, request.task_id)
        self.assertEqual(artifact.request_summary, request.user_goal)
        self.assertEqual(artifact.ordered_steps[0].step_id, "step-1")

    def test_deterministic_artifact_generation(self) -> None:
        """Produce identical artifacts for equivalent validated output."""

        request, draft, artifact = self._validated_output()
        graph = self.resolver.resolve(draft)
        report = self.validator.validate(graph)

        first = self.builder.build(request, graph, report)
        second = build_plan_artifact(request, graph, report)

        self.assertEqual(first, second)
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.artifact_id, artifact.artifact_id)

    def test_identifier_stability(self) -> None:
        """Keep artifact identifiers stable across repeated construction."""

        request, draft, _ = self._validated_output()
        graph = self.resolver.resolve(draft)
        report = self.validator.validate(graph)

        first = self.builder.build(request, graph, report)
        second = self.builder.build(request, graph, report)

        self.assertEqual(first.artifact_id, second.artifact_id)
        self.assertEqual(first.revision_id, second.revision_id)

    def test_schema_version_preservation(self) -> None:
        """Preserve schema version information through the builder."""

        request, draft, _ = self._validated_output()
        graph = self.resolver.resolve(draft)
        report = self.validator.validate(graph)

        artifact = self.builder.build(request, graph, report)

        self.assertEqual(artifact.schema_version, request.schema_version)
        self.assertEqual(artifact.schema_version, graph.schema_version)

    def test_serialization_compatibility(self) -> None:
        """Round-trip the built artifact through the existing serializer."""

        request, draft, _ = self._validated_output()
        graph = self.resolver.resolve(draft)
        report = self.validator.validate(graph)

        artifact = self.builder.build(request, graph, report)
        serialized = artifact.to_dict()

        self.assertEqual(PlanArtifact.from_dict(serialized), artifact)
        self.assertEqual(deserialize_plan_artifact(serialize_plan_artifact(artifact)), artifact)
        self.assertEqual(deserialize_plan_graph(serialize_plan_graph(graph)), graph)

    def test_malformed_input_handling(self) -> None:
        """Reject malformed validated planning output."""

        request, draft, _ = self._validated_output()
        graph = self.resolver.resolve(draft)
        report = self.validator.validate(graph)

        with self.assertRaises(MalformedPlanningArtifactInputError):
            self.builder.build("not-a-request", graph, report)  # type: ignore[arg-type]

        with self.assertRaises(MalformedPlanningArtifactInputError):
            self.builder.build(request, "not-a-graph", report)  # type: ignore[arg-type]

        with self.assertRaises(MalformedPlanningArtifactInputError):
            self.builder.build(request, graph, "not-a-report")  # type: ignore[arg-type]

        empty_graph = self.resolver.resolve(PlanDraft(
            task_id=request.task_id,
            request=request,
            subgoals=(),
            steps=(
                PlanStep(step_id="step-only", title="Only"),
            ),
        ))
        empty_report = self.validator.validate(empty_graph)
        self.assertEqual(empty_report.status, ValidationStatus.VALID)

    def test_backward_compatibility(self) -> None:
        """Continue to accept the existing artifact contract shape."""

        request, draft, _ = self._validated_output()
        graph = self.resolver.resolve(draft)
        report = self.validator.validate(graph)
        artifact = self.builder.build(request, graph, report)

        self.assertEqual(artifact, PlanArtifact.from_dict(artifact.to_dict()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
