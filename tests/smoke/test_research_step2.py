"""Smoke tests for Part 4 Step 2 research request normalization."""

import unittest

from qwen3_coder_next.research import (
    MalformedResearchRequestError,
    MalformedSourcePolicyError,
    ResearchRequest,
    ResearchRequestNormalizer,
    ResearchTaskType,
    SourceType,
    normalize_research_request,
)


class ResearchStep2SmokeTest(unittest.TestCase):
    """Verify deterministic request normalization and source policy shaping."""

    def test_successful_normalization(self) -> None:
        """Normalize raw research input into canonical contracts."""

        normalizer = ResearchRequestNormalizer()
        result = normalizer.normalize(
            "  Investigate repository docs drift  ",
            request_id="  req-007  ",
            task_type="investigation",
            target_repo="  Qwen-3-Coder-Next ",
            constraints=[" read-only ", " local-only ", ""],
            hints=[" docs/architecture.md ", " planning output "],
            source_policy={
                "allowed_sources": ["repo_file", "doc", "repo_file"],
                "preferred_sources": ["doc", "repo_file"],
                "blocked_sources": ["error_artifact"],
                "source_rank_weights": {"doc": 0.8, "repo_file": 1.0},
                "max_evidence_items": 7,
                "max_snippet_chars": 500,
                "cache_ttl_minutes": 15,
            },
        )

        self.assertIsInstance(result.request, ResearchRequest)
        self.assertEqual(result.request.request_id, "req-007")
        self.assertEqual(result.request.task_type, ResearchTaskType.INVESTIGATION)
        self.assertEqual(result.request.target_repo, "Qwen-3-Coder-Next")
        self.assertEqual(result.request.query_text, "Investigate repository docs drift")
        self.assertEqual(result.request.constraints, ("read-only", "local-only"))
        self.assertEqual(result.request.hints, ("docs/architecture.md", "planning output"))
        self.assertEqual(result.source_policy.allowed_sources, (SourceType.REPO_FILE, SourceType.DOC))
        self.assertEqual(result.source_policy.preferred_sources, (SourceType.DOC, SourceType.REPO_FILE))
        self.assertEqual(result.source_policy.blocked_sources, (SourceType.ERROR_ARTIFACT,))
        self.assertEqual(result.source_policy.max_evidence_items, 7)
        self.assertEqual(result.source_policy.max_snippet_chars, 500)
        self.assertEqual(result.source_policy.cache_ttl_minutes, 15)

    def test_deterministic_output(self) -> None:
        """Return the same normalized output for equivalent input."""

        payload = {
            "request_id": "req-001",
            "task_type": "bug",
            "target_repo": "repo",
            "query_text": "  Find broken docs  ",
            "constraints": ("a", "b"),
            "hints": ("x", "y"),
            "budget": {"time_ms": 1000, "source_limit": 3, "snippet_limit": 111},
            "source_policy": {
                "allowed_sources": ("repo_file", "doc"),
                "preferred_sources": ("repo_file",),
                "blocked_sources": ("error_artifact",),
                "source_rank_weights": {"doc": 0.8, "repo_file": 1.0},
            },
        }

        first = normalize_research_request(payload)
        second = normalize_research_request(payload)

        self.assertEqual(first, second)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_request_id_derivation_uses_canonical_json(self) -> None:
        """Derive a stable request identifier when one is not provided."""

        payload_one = {
            "task_type": "feature",
            "target_repo": "repo",
            "query_text": "Trace the research path",
            "constraints": ("x", "y"),
            "hints": ("a",),
            "source_policy": {"allowed_sources": ("repo_file",)},
        }
        payload_two = {
            "target_repo": "repo",
            "query_text": "Trace the research path",
            "task_type": "feature",
            "hints": ("a",),
            "constraints": ("x", "y"),
            "source_policy": {"allowed_sources": ("repo_file",)},
        }

        first = normalize_research_request(payload_one)
        second = normalize_research_request(payload_two)

        self.assertEqual(first.request.request_id, second.request.request_id)

    def test_malformed_request_handling(self) -> None:
        """Reject malformed request and policy payloads."""

        normalizer = ResearchRequestNormalizer()

        with self.assertRaises(MalformedResearchRequestError):
            normalizer.normalize("   ")

        with self.assertRaises(MalformedResearchRequestError):
            normalizer.normalize({"query_text": "ok", "budget": "bad"})  # type: ignore[arg-type]

        with self.assertRaises(MalformedSourcePolicyError):
            normalizer.normalize(
                {
                    "query_text": "ok",
                    "source_policy": {
                        "allowed_sources": ["repo_file"],
                        "blocked_sources": ["repo_file"],
                    },
                }
            )

    def test_serialization_compatibility(self) -> None:
        """Round-trip the normalization result through dict serialization."""

        result = normalize_research_request(
            {
                "request_id": "req-serialize",
                "task_type": "investigation",
                "target_repo": "repo",
                "query_text": "Serialize research request",
            }
        )

        self.assertEqual(result, type(result).from_dict(result.to_dict()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
