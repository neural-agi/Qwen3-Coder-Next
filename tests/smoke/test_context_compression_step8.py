import unittest

from qwen3_coder_next.context_compression import (
    CompressionTelemetry,
    ContextFallback,
    EvidenceChunk,
    FallbackResult,
    RankingResult,
    RetrievalIssue,
    RetrievalResult,
    ContextCompressionPipeline,
    CompressionConfig,
    SourceSpec,
    ContextRehydrator,
    ContextPackageCache,
    BudgetReport,
)


class ContextCompressionStep8Tests(unittest.TestCase):
    class Adapter:
        source_type = "fixture"

        def retrieve(self, request, source):
            return (EvidenceChunk(source.source_id, "src/app.py", "Error: missing config", 1, 1, (source.fingerprint,), 1, "2026-01-01T00:00:00Z", .9),)

    def test_fallback_only_activates_for_successful_empty_ranking(self):
        chunks = (EvidenceChunk("b", "b.py", "b", 1, 1), EvidenceChunk("a", "a.py", "a", 1, 1))
        result = ContextFallback().select(RetrievalResult(chunks), RankingResult())
        self.assertTrue(result.activated)
        self.assertEqual(result.reason_code, "ranking_empty_after_successful_retrieval")
        self.assertEqual(result.chunks[0].source_id, "a")
        self.assertEqual(ContextFallback().select(RetrievalResult(chunks, (RetrievalIssue("repo", "failed", "error"),)), RankingResult()).activated, False)

    def test_fallback_does_not_replace_nonempty_ranking(self):
        chunk = EvidenceChunk("a", "a.py", "a", 1, 1)
        result = ContextFallback().select(RetrievalResult((chunk,)), RankingResult((chunk,)))
        self.assertEqual(result, FallbackResult((chunk,), False, ""))

    def test_telemetry_is_structured_deterministic_and_metadata_only(self):
        first = CompressionTelemetry()
        second = CompressionTelemetry()
        for recorder in (first, second):
            recorder.record("retrieval", {"candidate_count": 2, "status": "success"})
            recorder.record("fallback", {"activated": False, "reason_code": ""})
        self.assertEqual([event.to_dict() for event in first.events], [event.to_dict() for event in second.events])
        self.assertNotIn("excerpt", first.events[0].to_dict())
        with self.assertRaises(ValueError):
            first.record("", {})

    def test_pipeline_runs_stages_cache_and_emits_events(self):
        pipeline = ContextCompressionPipeline(__import__("qwen3_coder_next.context_compression", fromlist=["ContextRetriever"]).ContextRetriever((self.Adapter(),)))
        raw = {"task_id": "task", "agent_role": "planner", "intent": "inspect failure", "token_budget": 100, "seed_sources": ("repo",), "freshness_window": 0}
        sources = (SourceSpec("repo", "fixture", "snapshot-1"),)
        first = pipeline.run(raw, sources, CompressionConfig(100, .5, "extractive", .8, .5), 5)
        second = pipeline.run(raw, sources, CompressionConfig(100, .5, "extractive", .8, .5), 5)
        self.assertEqual(first.status, "success")
        self.assertEqual(second.status, "cache_hit")
        self.assertEqual(first.package.to_dict(), second.package.to_dict())
        self.assertTrue(any(event["event_type"] == "retrieval" for event in first.telemetry))
        self.assertTrue(any(event["event_type"] == "summary" for event in first.telemetry))
        self.assertTrue(any(event["event_type"] == "budget" for event in first.telemetry))
        self.assertTrue(any(event["event_type"] == "package" for event in first.telemetry))
        self.assertTrue(first.package.coverage_notes)

    def test_empty_ranking_fallback_produces_complete_package_and_event(self):
        class EmptyRanker:
            def rank(self, request, chunks, plan):
                return RankingResult()

        from qwen3_coder_next.context_compression import ContextRetriever
        pipeline = ContextCompressionPipeline(ContextRetriever((self.Adapter(),)), ranker=EmptyRanker())
        raw = {"task_id": "task", "agent_role": "planner", "intent": "inspect failure", "token_budget": 100, "seed_sources": ("repo",), "freshness_window": 0}
        result = pipeline.run(raw, (SourceSpec("repo", "fixture", "snapshot-1"),), CompressionConfig(100, .5, "extractive", .8, .5))
        self.assertEqual(result.status, "success")
        self.assertTrue(result.fallback_activated)
        self.assertTrue(result.package.selected_chunks)
        self.assertTrue(any(event["event_type"] == "fallback" for event in result.telemetry))

    def test_cache_rejects_entry_above_configured_ceiling(self):
        cache = ContextPackageCache()
        package = __import__("qwen3_coder_next.context_compression", fromlist=["ContextPackage"]).ContextPackage("p", "t", budget_used=9)
        report = BudgetReport(10, 9, 0)
        with self.assertRaises(ValueError):
            cache.put("k", package, report, CompressionConfig(8, .5, "extractive", .8, .5))

    def test_rehydration_requires_matching_source_fingerprint(self):
        from qwen3_coder_next.context_compression import ContextPackager, BudgetManager, EvidenceSummarizer, SourcePlan, SourcePlanEntry, ContextRequest
        request = ContextRequest("task", "planner", "inspect failure", 100, ("repo",))
        chunk = EvidenceChunk("repo", "src/app.py", "Error: missing config", 1, 1, ("snapshot-1",), 1, "2026-01-01T00:00:00Z", .9)
        config = CompressionConfig(100, .5, "extractive", .8, .5)
        summary = EvidenceSummarizer().summarize(request, (chunk,), config)
        budget = BudgetManager().apply(request, summary, 100, 5, config)
        package = ContextPackager().package(request, summary, budget, (chunk,), SourcePlan((SourcePlanEntry("repo", "fixture", "snapshot-1", 1),)), config)
        restored = ContextRehydrator().rehydrate(package, SourcePlan((SourcePlanEntry("repo", "fixture", "snapshot-1", 1),)), {"repo": lambda location: chunk})
        self.assertEqual(restored, (chunk,))
        with self.assertRaises(ValueError):
            ContextRehydrator().rehydrate(package, SourcePlan((SourcePlanEntry("repo", "fixture", "stale", 1),)), {"repo": lambda location: chunk})


if __name__ == "__main__":
    unittest.main()
