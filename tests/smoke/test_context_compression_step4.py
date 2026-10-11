import unittest

from qwen3_coder_next.context_compression import CompressionConfig, ContextRequest, EvidenceChunk, EvidenceDeduplicator, EvidenceRanker, SourcePlan, SourcePlanEntry


class ContextCompressionStep4Tests(unittest.TestCase):
    def setUp(self):
        self.request = ContextRequest("task", "planner", "target callers", 100, (), 0)
        self.plan = SourcePlan((SourcePlanEntry("high", "repository_snapshot", "fp-high", 1.0), SourcePlanEntry("low", "memory", "fp-low", 0.2)))
        self.config = CompressionConfig(100, 0.5, "extractive", 0.8, 0.5)

    def test_supported_scores_and_deterministic_ordering(self):
        chunks = (
            EvidenceChunk("low", "b.py:1", "unrelated", 0.5, 0.5),
            EvidenceChunk("high", "a.py:1", "target callers", 0.5, 0.5),
        )
        first = EvidenceRanker().rank(self.request, chunks, self.plan)
        second = EvidenceRanker().rank(self.request, tuple(reversed(chunks)), self.plan)
        self.assertEqual(first, second)
        self.assertEqual(first.chunks[0].location, "a.py:1")
        self.assertGreater(first.chunks[0].score, first.chunks[1].score)

    def test_exact_deduplication_merges_provenance(self):
        duplicate_a = EvidenceChunk("high", "a.py:1", "same", 0.4, 0.5, ("repo-fp",))
        duplicate_b = EvidenceChunk("low", "a.py:1", "same", 0.8, 0.9, ("memory-fp",))
        result = EvidenceDeduplicator().deduplicate((duplicate_b, duplicate_a), self.config)
        self.assertEqual(len(result.chunks), 1)
        self.assertEqual(result.chunks[0].source_id, "high")
        self.assertEqual(result.chunks[0].score, 0.8)
        self.assertEqual(result.chunks[0].provenance, ("memory-fp", "repo-fp", "source:high", "source:low"))

    def test_empty_and_invalid_inputs_are_explicit(self):
        self.assertEqual(EvidenceRanker().rank(self.request, (), self.plan).chunks, ())
        self.assertEqual(EvidenceDeduplicator().deduplicate((), self.config).chunks, ())
        with self.assertRaises(ValueError):
            EvidenceRanker().rank(self.request, ("bad",), self.plan)
        with self.assertRaises(ValueError):
            EvidenceDeduplicator().deduplicate((EvidenceChunk("s", "l", "x", 0.5, 0.5),), object())

    def test_threshold_is_validated_but_no_fuzzy_matching_is_invented(self):
        near = (EvidenceChunk("a", "same.py:1", "same text", 0.5, 0.5), EvidenceChunk("b", "same.py:1", "same text plus detail", 0.5, 0.5))
        result = EvidenceDeduplicator().deduplicate(near, self.config)
        self.assertEqual(len(result.chunks), 2)
        with self.assertRaises(ValueError):
            CompressionConfig(100, 0.5, "extractive", 1.1, 0.5)


if __name__ == "__main__":
    unittest.main()
