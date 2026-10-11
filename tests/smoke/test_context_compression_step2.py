import unittest

from qwen3_coder_next.context_compression import ContextRequest, ContextRequestNormalizer, SourceResolver, SourceSpec


class ContextCompressionStep2Tests(unittest.TestCase):
    def test_normalization_is_canonical_and_preserves_seed_sources(self):
        raw = {"task_id": "task", "agent_role": "planner", "intent": " find callers ", "token_budget": 100, "seed_sources": ["b", "a", "a"], "freshness_window": 2}
        normalized = ContextRequestNormalizer().normalize(raw)
        self.assertEqual(normalized, ContextRequest("task", "planner", "find callers", 100, ("a", "b"), 2))
        self.assertEqual(normalized, ContextRequestNormalizer().normalize({**raw, "seed_sources": ("a", "b")}))

    def test_normalizer_rejects_missing_and_invalid_inputs(self):
        normalizer = ContextRequestNormalizer()
        with self.assertRaises(ValueError):
            normalizer.normalize({"agent_role": "planner"})
        with self.assertRaises(ValueError):
            normalizer.normalize({"task_id": "t", "agent_role": "planner", "intent": "", "token_budget": 1, "seed_sources": (), "freshness_window": 0})
        with self.assertRaises(ValueError):
            normalizer.normalize(object())

    def test_source_resolution_is_deterministic_and_explicit_about_unavailable_sources(self):
        request = ContextRequest("task", "planner", "intent", 100, ("repo", "missing"), 2)
        specs = (SourceSpec("repo", "repository_snapshot", "repo-fp", True, 3), SourceSpec("memory", "memory_state", "mem-fp", False, 5))
        resolver = SourceResolver()
        first = resolver.resolve(request, specs)
        second = resolver.resolve(request, tuple(reversed(specs)))
        self.assertEqual(first, second)
        self.assertEqual(tuple(item.source_id for item in first.entries), ("missing", "repo"))
        self.assertEqual(first.entries[0].status, "unavailable")
        self.assertEqual(first.entries[1].status, "available")

    def test_source_resolution_marks_stale_and_rejects_malformed_sources(self):
        request = ContextRequest("task", "planner", "intent", 100, ("repo",), 5)
        result = SourceResolver().resolve(request, (SourceSpec("repo", "repository_snapshot", "fp", True, 2),))
        self.assertEqual(result.entries[0].status, "stale")
        with self.assertRaises(ValueError):
            SourceResolver().resolve(request, (SourceSpec("repo", "repository_snapshot", "", True),))
        with self.assertRaises(ValueError):
            SourceResolver().resolve(request, ("bad",))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
