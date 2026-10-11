import tempfile
import unittest
from pathlib import Path

from qwen3_coder_next.context_compression import (
    ContextRetriever,
    ContextRequest,
    GraphTraversalAdapter,
    RepositorySnapshotAdapter,
    SourcePlan,
    SourcePlanEntry,
    SourceResolver,
    SourceSpec,
)
from qwen3_coder_next.graph import GraphNode, GraphQuery, GraphSnapshot, GraphStore, NodeKind
from qwen3_coder_next.repo_intelligence import FileClassifier, RepositoryScanner, SummaryGenerator
from qwen3_coder_next.repo_intelligence.schemas import RepoSnapshot


class ContextCompressionStep3Tests(unittest.TestCase):
    def test_repository_summary_adapter_returns_provenance_and_deterministic_chunks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
            scan = RepositoryScanner().scan(root)
            files = FileClassifier().classify_many(scan.files)
            summaries = SummaryGenerator().summarize_files(files, contents={"src/main.py": "print('ok')\n"})
            snapshot = RepoSnapshot("repo", root.as_posix(), "rev", "time", len(files), len(scan.folders), "hash", files, scan.folders, (), summaries)
            request = ContextRequest("task", "planner", "main", 50, ("main.py",), 0)
            source = SourcePlan((SourcePlanEntry("repo", "repository_snapshot", "hash", 1.0),))
            result = ContextRetriever((RepositorySnapshotAdapter(snapshot),)).retrieve(request, source)
            self.assertEqual(result.issues, ())
            self.assertEqual(result, ContextRetriever((RepositorySnapshotAdapter(snapshot),)).retrieve(request, source))
            self.assertTrue(result.chunks[0].provenance)
            self.assertEqual(result.chunks[0].source_id, "repo")

    def test_partial_availability_and_unsupported_sources_are_explicit(self):
        request = ContextRequest("task", "planner", "intent", 50, (), 0)
        plan = SourceResolver().resolve(request, (SourceSpec("unknown", "qdrant", "fp"), SourceSpec("missing", "memory", "fp", False)))
        result = ContextRetriever().retrieve(request, plan)
        self.assertEqual(tuple(issue.status for issue in result.issues), ("unavailable", "unsupported"))
        self.assertEqual(result.chunks, ())

    def test_invalid_fingerprint_and_adapter_output_are_failures(self):
        request = ContextRequest("task", "planner", "intent", 50, (), 0)
        plan = SourcePlan((SourcePlanEntry("repo", "repository_snapshot", "wrong", 1.0),))
        adapter = RepositorySnapshotAdapter(RepoSnapshot("repo", ".", "rev", "time", 0, 0, "right"))
        result = ContextRetriever((adapter,)).retrieve(request, plan)
        self.assertEqual(result.issues[0].status, "failed")

    def test_graph_adapter_uses_published_graph_query_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            node = GraphNode.create("repo", NodeKind.FUNCTION, "run", "run", "main.py", "python", "rev")
            graph = GraphSnapshot("graph-snap", "repo", "rev", (node,), ())
            store = GraphStore(Path(directory))
            store.publish(graph)
            request = ContextRequest("task", "planner", "run", 50, (), 0)
            plan = SourcePlan((SourcePlanEntry("graph", "graph_snapshot", "graph-snap", 1.0),))
            adapter = GraphTraversalAdapter(store, "repo", node.node_id, GraphQuery("repo", "rev"))
            result = ContextRetriever((adapter,)).retrieve(request, plan)
            self.assertEqual(result.issues, ())
            self.assertEqual(result.chunks[0].location, "main.py")
            self.assertIn("graph-snap", result.chunks[0].provenance)


if __name__ == "__main__":
    unittest.main()
