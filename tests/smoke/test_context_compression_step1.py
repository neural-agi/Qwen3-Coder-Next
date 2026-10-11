import unittest
from dataclasses import FrozenInstanceError

from qwen3_coder_next.context_compression import (
    BudgetReport,
    CompressionConfig,
    ContextPackage,
    ContextRequest,
    EvidenceChunk,
    canonical_package_id,
    compression_config_fingerprint,
    context_request_fingerprint,
)


class ContextCompressionStep1Tests(unittest.TestCase):
    def test_all_contracts_construct_and_round_trip(self):
        request = ContextRequest("task-1", "planner", "find callers", 100, ("b", "a"), 7)
        chunk = EvidenceChunk("source-1", "pkg/a.py:1", "def run():", 0.9, 0.8, ("pkg/a.py:1",))
        package = ContextPackage("package-1", request.task_id, (chunk,), "brief", 12, ("source-2",), {"source-1": ("pkg/a.py:1",)})
        report = BudgetReport(20, 12, 8, ("source-2",), ("budget",))
        config = CompressionConfig(100, 0.5, "extractive", 0.8, 0.2)
        self.assertEqual(ContextRequest.from_dict(request.to_dict()), request)
        self.assertEqual(EvidenceChunk.from_dict(chunk.to_dict()), chunk)
        self.assertEqual(ContextPackage.from_dict(package.to_dict()), package)
        self.assertEqual(BudgetReport.from_dict(report.to_dict()), report)
        self.assertEqual(CompressionConfig.from_dict(config.to_dict()), config)
        self.assertEqual(request.seed_sources, ("a", "b"))
        self.assertEqual(package.provenance_map, (("source-1", ("pkg/a.py:1",)),))

    def test_validation_and_budget_boundaries(self):
        with self.assertRaises(ValueError):
            ContextRequest("", "planner", "intent", 1)
        with self.assertRaises(ValueError):
            ContextRequest("task", "planner", "intent", 0)
        with self.assertRaises(ValueError):
            EvidenceChunk("s", "l", "e", 1.1, 0.5)
        with self.assertRaises(ValueError):
            EvidenceChunk("s", "l", "e", 0.5, -0.1)
        with self.assertRaises(ValueError):
            BudgetReport(10, 8, 3)
        with self.assertRaises(ValueError):
            CompressionConfig(0, 0.5, "style", 0.5, 0.5)
        with self.assertRaises(ValueError):
            ContextPackage("p", "t", (), "", 0, (), "bad")

    def test_immutable_contracts_and_deterministic_identifiers(self):
        request_a = ContextRequest("task", "role", "intent", 10, ("b", "a"), 1)
        request_b = ContextRequest("task", "role", "intent", 10, ("a", "b"), 1)
        self.assertEqual(context_request_fingerprint(request_a), context_request_fingerprint(request_b))
        config = CompressionConfig(10, 0.5, "extractive", 0.5, 0.5)
        self.assertEqual(compression_config_fingerprint(config), compression_config_fingerprint(config))
        self.assertEqual(canonical_package_id("task", "request", ("b", "a"), "policy"), canonical_package_id("task", "request", ("a", "b"), "policy"))
        with self.assertRaises(FrozenInstanceError):
            config.max_tokens = 20  # type: ignore[misc]

    def test_malformed_payloads_and_public_imports(self):
        for factory in (ContextRequest.from_dict, EvidenceChunk.from_dict, ContextPackage.from_dict, BudgetReport.from_dict, CompressionConfig.from_dict):
            with self.assertRaises((KeyError, ValueError)):
                factory({})
        with self.assertRaises(ValueError):
            context_request_fingerprint(object())


if __name__ == "__main__":
    unittest.main()
