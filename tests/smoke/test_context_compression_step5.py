import unittest

from qwen3_coder_next.context_compression import (
    CompressionConfig,
    ContextRequest,
    EvidenceChunk,
    EvidenceSummarizer,
    SummaryPolicy,
    SummaryPolicyRegistry,
)


class ContextCompressionStep5Tests(unittest.TestCase):
    def setUp(self):
        self.request = ContextRequest("task", "planner", "inspect failing command", 100)
        self.config = CompressionConfig(100, 0.5, "extractive", 0.8, 0.5)

    def test_extracts_actionable_facts_and_provenance(self):
        result = EvidenceSummarizer().summarize(self.request, [EvidenceChunk("repo", "src/app.py", "run: python -m tests\nError: missing config", 1, 1, (), 1, "2026-01-01T00:00:00Z", .9)], self.config)
        self.assertIn("python -m tests", result.summary)
        self.assertEqual(result.claims[0].source_id, "repo")
        self.assertEqual(result.claims[0].location, "src/app.py")
        self.assertTrue(result.highlights)

    def test_policy_identity_and_determinism(self):
        policies = SummaryPolicyRegistry((SummaryPolicy("planner", "planner-v2", 1),))
        summarizer = EvidenceSummarizer(policies)
        chunks = [EvidenceChunk("b", "b.txt", "B", .5, .2, (), 1, "2026-01-01T00:00:00Z", .5), EvidenceChunk("a", "a.txt", "A", .5, .2, (), 1, "2026-01-01T00:00:00Z", .5)]
        first = summarizer.summarize(self.request, chunks, self.config)
        second = summarizer.summarize(self.request, list(reversed(chunks)), self.config)
        self.assertEqual(first, second)
        self.assertEqual(first.policy_version, "planner-v2")

    def test_omissions_and_budget_overflow_are_explicit(self):
        chunk = EvidenceChunk("repo", "x.py", "first\nsecond\nthird", 1, 1, (), 1, "2026-01-01T00:00:00Z", 1)
        result = EvidenceSummarizer().summarize(self.request, (chunk,), self.config, summary_budget=3)
        self.assertTrue(result.omissions)
        self.assertTrue(result.budget_exceeded)

    def test_empty_and_malformed_inputs(self):
        self.assertEqual(EvidenceSummarizer().summarize(self.request, (), self.config).summary, "")
        with self.assertRaises(ValueError):
            EvidenceSummarizer().summarize(self.request, ["bad"], self.config)
        with self.assertRaises(ValueError):
            EvidenceSummarizer().summarize(self.request, (), self.config, 0)


if __name__ == "__main__":
    unittest.main()
