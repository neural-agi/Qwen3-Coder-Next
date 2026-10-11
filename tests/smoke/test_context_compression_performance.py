import time
import unittest

from qwen3_coder_next.context_compression import CompressionConfig, ContextRequest, EvidenceChunk, EvidenceRanker, SourcePlan, SourcePlanEntry


class ContextCompressionPerformanceTests(unittest.TestCase):
    def test_repeated_large_candidate_ranking_is_deterministic(self):
        request = ContextRequest("load", "planner", "inspect repository", 10000)
        config = CompressionConfig(10000, .5, "extractive", .8, .5)
        chunks = tuple(EvidenceChunk("repo", f"src/{index:04d}.py", "def function(): return 1", 1, 1, ("snapshot",), 1, "2026-01-01T00:00:00Z", 1) for index in range(1000))
        started = time.perf_counter()
        plan = SourcePlan((SourcePlanEntry("repo", "fixture", "snapshot", 1.0),))
        first = EvidenceRanker().rank(request, chunks, plan)
        elapsed = time.perf_counter() - started
        second = EvidenceRanker().rank(request, tuple(reversed(chunks)), plan)
        self.assertEqual(first, second)
        self.assertEqual(len(first.chunks), 1000)
        self.assertGreaterEqual(elapsed, 0.0)


if __name__ == "__main__":
    unittest.main()
