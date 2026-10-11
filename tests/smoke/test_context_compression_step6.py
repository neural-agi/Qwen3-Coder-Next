import unittest

from qwen3_coder_next.context_compression import (
    BudgetManager,
    CompressionConfig,
    ContextRequest,
    EvidenceChunk,
    EvidenceSummarizer,
    estimate_tokens,
)


class ContextCompressionStep6Tests(unittest.TestCase):
    def setUp(self):
        self.request = ContextRequest("task", "planner", "inspect failure", 100)
        self.config = CompressionConfig(100, 0.5, "extractive", 0.8, 0.5)
        self.summary = EvidenceSummarizer().summarize(
            self.request,
            [
                EvidenceChunk("b", "b.py", "second detail", 1, 1, (), 1, "2026-01-01T00:00:00Z", 1),
                EvidenceChunk("a", "a.py", "first detail", 1, 1, (), 1, "2026-01-01T00:00:00Z", 1),
            ],
            self.config,
        )

    def test_budget_boundary_and_accounting(self):
        manager = BudgetManager()
        result = manager.apply(self.request, self.summary, 20, 2, self.config)
        self.assertLessEqual(result.report.used_budget + result.report.reserved_budget, result.report.requested_budget)
        self.assertEqual(result.report.used_budget, estimate_tokens(result.rendered_summary))

    def test_deterministic_trimming_and_dropped_sources(self):
        manager = BudgetManager()
        first = manager.apply(self.request, self.summary, 12, 1, self.config)
        second = manager.apply(self.request, self.summary, 12, 1, self.config)
        self.assertEqual(first, second)
        self.assertTrue(first.report.dropped_sources)
        self.assertTrue(first.report.reason_codes)

    def test_reserved_budget_and_impossible_required_content(self):
        manager = BudgetManager()
        with self.assertRaises(ValueError):
            manager.apply(self.request, self.summary, 2, 3, self.config)
        result = manager.apply(self.request, self.summary, 1, 0, self.config)
        self.assertFalse(result.feasible)
        self.assertIn("required_content_exceeds_budget", result.report.reason_codes)
        self.assertEqual(result.report.used_budget + result.report.reserved_budget, 0)

    def test_empty_summary_is_valid(self):
        result = BudgetManager().apply(self.request, EvidenceSummarizer().summarize(self.request, (), self.config), 20, 2, self.config)
        self.assertTrue(result.feasible)
        self.assertFalse(result.accepted_claims)


if __name__ == "__main__":
    unittest.main()
