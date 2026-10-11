import unittest

from qwen3_coder_next.context_compression import (
    BudgetManager,
    CompressionConfig,
    ContextPackageCache,
    ContextPackager,
    ContextRequest,
    ContextRetriever,
    EvidenceChunk,
    EvidenceSummarizer,
    SourcePlan,
    SourcePlanEntry,
    context_cache_key,
)


class ContextCompressionStep7Tests(unittest.TestCase):
    def setUp(self):
        self.request = ContextRequest("task", "planner", "inspect failure", 100, ("repo",))
        self.config = CompressionConfig(100, 0.5, "extractive", 0.8, 0.5)
        self.plan = SourcePlan((SourcePlanEntry("repo", "repository", "snapshot-1", 1.0),))
        self.evidence = (EvidenceChunk("repo", "src/app.py", "Error: missing config", 1, 1, ("snapshot-1",), 1, "2026-01-01T00:00:00Z", .9),)
        summary = EvidenceSummarizer().summarize(self.request, self.evidence, self.config)
        self.budget = BudgetManager().apply(self.request, summary, 100, 5, self.config)

    def test_packaging_is_deterministic_and_rehydratable(self):
        packager = ContextPackager()
        first = packager.package(self.request, EvidenceSummarizer().summarize(self.request, self.evidence, self.config), self.budget, self.evidence, self.plan, self.config)
        second = packager.package(self.request, EvidenceSummarizer().summarize(self.request, self.evidence, self.config), self.budget, tuple(reversed(self.evidence)), self.plan, self.config)
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.selected_chunks[0].provenance, ("snapshot-1",))
        self.assertEqual(first.provenance_map, (("repo", ("src/app.py",)),))
        self.assertEqual(first.to_dict(), type(first).from_dict(first.to_dict()).to_dict())

    def test_packager_rejects_missing_provenance_or_infeasible_budget(self):
        packager = ContextPackager()
        empty_summary = EvidenceSummarizer().summarize(self.request, (), self.config)
        infeasible = BudgetManager().apply(self.request, empty_summary, 1, 0, self.config)
        with self.assertRaises(ValueError):
            packager.package(self.request, empty_summary, infeasible, (), self.plan, self.config)
        with self.assertRaises(ValueError):
            packager.package(self.request, EvidenceSummarizer().summarize(self.request, self.evidence, self.config), self.budget, (), self.plan, self.config)

    def test_cache_hits_misses_and_invalid_entries_are_distinct(self):
        key = context_cache_key(self.request, self.plan, self.config, "extractive-default-v1", 5)
        cache = ContextPackageCache()
        self.assertEqual(cache.get(key).status, "miss")
        package = ContextPackager().package(self.request, EvidenceSummarizer().summarize(self.request, self.evidence, self.config), self.budget, self.evidence, self.plan, self.config)
        cache.put(key, package, self.budget.report)
        self.assertEqual(cache.get(key).status, "hit")
        cache._entries[key]["payload"] = {"broken": True}
        self.assertEqual(cache.get(key).status, "invalid")

    def test_cache_key_changes_for_fingerprint_policy_and_budget(self):
        base = context_cache_key(self.request, self.plan, self.config, "v1", 5, self.evidence)
        changed_plan = SourcePlan((SourcePlanEntry("repo", "repository", "snapshot-2", 1.0),))
        self.assertNotEqual(base, context_cache_key(self.request, changed_plan, self.config, "v1", 5))
        self.assertNotEqual(base, context_cache_key(self.request, self.plan, self.config, "v2", 5))
        self.assertNotEqual(base, context_cache_key(self.request, self.plan, self.config, "v1", 6))
        changed = EvidenceChunk("repo", "src/app.py", "changed", 1, 1, ("snapshot-1",), 1, "2026-01-01T00:00:00Z", .9)
        self.assertNotEqual(base, context_cache_key(self.request, self.plan, self.config, "v1", 5, (changed,)))


if __name__ == "__main__":
    unittest.main()
