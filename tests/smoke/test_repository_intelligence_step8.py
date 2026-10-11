import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from qwen3_coder_next.graph import EdgeKind, GraphConsistencyValidator, GraphQuery, GraphStore, InvalidationEvent, InvalidationManager, QueryDirection, RebuildInput
from qwen3_coder_next.repo_intelligence import (
    FileClassifier,
    RepositoryGraphService,
    RepositoryQueryResult,
    RepositoryQueryService,
    RepositoryScanner,
    serialize_snapshot,
)
from qwen3_coder_next.repo_intelligence.schemas import FileRecord, FolderRecord, RepoSnapshot, SummaryRecord


class RepositoryIntelligenceStep8Tests(unittest.TestCase):
    def setUp(self):
        self.files = (
            FileRecord("src/main.py", "src/main.py", "source", "python", 10, "a"),
            FileRecord("src/theme.css", "src/theme.css", "source", "css", 10, "b"),
            FileRecord("README.md", "README.md", "documentation", "unknown", 10, "c"),
        )
        self.folders = (FolderRecord("src", 2, 0),)
        self.summaries = (
            SummaryRecord("s1", "src/main.py", "python source entry point", "derived"),
            SummaryRecord("s2", "src/theme.css", "css styling", "derived"),
        )
        self.snapshot = RepoSnapshot("repo", "/tmp/repo", "snapshot-1", "stable", 3, 1, "hash", self.files, self.folders, (), self.summaries)
        self.service = RepositoryQueryService()

    def _snapshot(self, root: Path) -> RepoSnapshot:
        scan = RepositoryScanner().scan(root)
        files = FileClassifier().classify_many(scan.files)
        return RepoSnapshot(
            "repo-step8", root.resolve().as_posix(), "repo-revision-1", "fixture-time",
            len(files), len(scan.folders), "fixture-content", files, scan.folders,
        )

    def test_build_publish_query_and_export_preserve_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pkg").mkdir()
            (root / "pkg" / "lib.py").write_text("def target():\n    return 1\n", encoding="utf-8")
            (root / "pkg" / "main.py").write_text("from pkg.lib import target\ntarget()\n", encoding="utf-8")
            snapshot = self._snapshot(root)
            service = RepositoryGraphService()
            graph = service.build(snapshot)
            self.assertEqual(graph.repo_id, snapshot.repository_id)
            self.assertEqual(graph.revision_id, snapshot.snapshot_id)
            self.assertEqual({node.qualified_name for node in graph.nodes}, {"pkg/lib.py", "pkg/main.py", "target"})
            self.assertEqual({edge.kind for edge in graph.edges}, {EdgeKind.DEFINES, EdgeKind.IMPORTS, EdgeKind.CALLS})
            GraphConsistencyValidator().validate(graph)
            self.assertTrue(all(node.revision_id == snapshot.snapshot_id for node in graph.nodes))
            store = GraphStore(root / ".graph")
            published = service.publish(snapshot, store)
            self.assertEqual(store.load_current(snapshot.repository_id), published)
            module = next(node for node in graph.nodes if node.file_path == "pkg/main.py" and node.qualified_name.endswith("main.py"))
            query = GraphQuery(snapshot.repository_id, snapshot.snapshot_id, edge_filters=(EdgeKind.CALLS,), depth=1, direction=QueryDirection.OUTGOING)
            result = service.query_published(store, snapshot.repository_id, module.node_id, query)
            self.assertEqual(result.root_nodes, (module.node_id,))
            self.assertIn("GraphSnapshot", service.export_published(store, snapshot.repository_id, "text"))

    def test_edit_rebuilds_only_affected_graph_region(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "stable.py").write_text("def stable():\n    return 1\n", encoding="utf-8")
            (root / "changed.py").write_text("def old():\n    return 1\n", encoding="utf-8")
            service = RepositoryGraphService()
            initial = service.build(self._snapshot(root))
            (root / "changed.py").write_text("def renamed():\n    return 1\n", encoding="utf-8")
            refreshed_snapshot = self._snapshot(root)
            rebuilt = service.build(refreshed_snapshot)
            stale = InvalidationManager().reconcile(
                initial,
                InvalidationEvent("repo-step8", ("changed.py",), revision_id=refreshed_snapshot.snapshot_id),
                RebuildInput(
                    tuple(node for node in rebuilt.nodes if node.file_path == "changed.py"),
                    tuple(edge for edge in rebuilt.edges if any(node.node_id == edge.from_node or node.node_id == edge.to_node for node in rebuilt.nodes if node.file_path == "changed.py")),
                ),
            )
            self.assertIn("renamed", {node.qualified_name for node in stale.snapshot.nodes})
            self.assertIn("stable", {node.qualified_name for node in stale.snapshot.nodes})
            self.assertNotIn("old", {node.qualified_name for node in stale.snapshot.nodes})

    def test_build_is_deterministic_and_unsupported_files_are_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            (root / "notes.md").write_text("not parsed\n", encoding="utf-8")
            snapshot = self._snapshot(root)
            service = RepositoryGraphService()
            self.assertEqual(service.build(snapshot), service.build(snapshot))

    def test_invalid_snapshot_store_and_export_inputs_are_rejected(self):
        service = RepositoryGraphService()
        with self.assertRaises(ValueError):
            service.build(object())
        with self.assertRaises(ValueError):
            service.export_published(object(), "repo", "json")

    def test_prefix_type_language_and_summary_queries(self):
        result = self.service.query(self.snapshot, path_prefix="src", file_type="source", language="PYTHON")
        self.assertEqual(tuple(item.normalized_path for item in result.files), ("src/main.py",))
        self.assertEqual(tuple(item.path for item in result.folders), ("src",))
        summary_result = self.service.query(self.snapshot, summary_text="ENTRY")
        self.assertEqual(tuple(item.target_path for item in summary_result.summaries), ("src/main.py",))

    def test_empty_and_no_match_results_are_stable(self):
        empty = self.service.query(self.snapshot)
        self.assertEqual(empty, self.service.query(self.snapshot, path_prefix="/"))
        no_match = self.service.query(self.snapshot, path_prefix="missing")
        self.assertEqual(no_match, RepositoryQueryResult("snapshot-1"))

    def test_ordering_repeatability_and_read_only_behavior(self):
        before = serialize_snapshot(self.snapshot)
        first = self.service.query(self.snapshot, path_prefix="src")
        second = self.service.query(self.snapshot, path_prefix="src")
        self.assertEqual(first, second)
        self.assertEqual(serialize_snapshot(self.snapshot), before)
        with self.assertRaises(FrozenInstanceError):
            first.files += (self.files[0],)  # type: ignore[misc]

    def test_malformed_query_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            self.service.query("bad")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            self.service.query(self.snapshot, language=3)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
