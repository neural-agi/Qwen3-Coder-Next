"""Smoke tests for Part 3 Step 2 planning request normalization."""

import unittest

from qwen3_coder_next.planning import (
    MalformedPlannerRequestError,
    PlannerRequest,
    PlannerRequestNormalizer,
    normalize_planner_request,
)


class PlanningStep2SmokeTest(unittest.TestCase):
    """Verify deterministic request normalization behavior."""

    def test_successful_normalization(self) -> None:
        """Normalize raw request text into a canonical planner request."""

        normalizer = PlannerRequestNormalizer()
        result = normalizer.normalize(
            "  Add   planning support  ",
            metadata={"owner": "  Team A ", "priority": 2, "tags": ["alpha", "beta"]},
            constraints=[" no database ", "local only", ""],
            source_context=["session notes", "architecture docs"],
            environment={"branch": " feature/planning ", "repo": "Qwen3-Coder-Next"},
        )

        self.assertIsInstance(result.request, PlannerRequest)
        self.assertEqual(result.request.user_goal, "Add planning support")
        self.assertEqual(result.request.constraints, ("no database", "local only"))
        self.assertEqual(result.request.source_context, ("session notes", "architecture docs"))
        self.assertEqual(result.request.environment["branch"], "feature/planning")
        self.assertEqual(result.metadata["owner"], "Team A")
        self.assertEqual(result.metadata["tags"], ("alpha", "beta"))

    def test_deterministic_output(self) -> None:
        """Return the same normalized output for the same input."""

        payload = {
            "task_id": "task-001",
            "raw_text": "  Add planning support ",
            "constraints": ("a", "b"),
            "metadata": {"z": 2, "a": 1},
            "source_context": ("context-1",),
            "environment": {"branch": "main", "repo": "repo"},
        }
        first = normalize_planner_request(payload)
        second = normalize_planner_request(payload)

        self.assertEqual(first, second)
        self.assertEqual(first.request, second.request)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_malformed_request_handling(self) -> None:
        """Reject empty or invalid request inputs."""

        normalizer = PlannerRequestNormalizer()

        with self.assertRaises(MalformedPlannerRequestError):
            normalizer.normalize("   ")

        with self.assertRaises(MalformedPlannerRequestError):
            normalizer.normalize({"metadata": "not-a-mapping"})

    def test_serialization_compatibility(self) -> None:
        """Round-trip the normalization result through serialization."""

        result = normalize_planner_request("Plan a feature")
        self.assertEqual(
            result,
            type(result).from_dict(result.to_dict()),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
