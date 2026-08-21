import tempfile
import unittest
from pathlib import Path

from qwen3_coder_next.graph import EdgeKind, GraphEdge, GraphNode, GraphSnapshot, GraphStore, NodeKind, serialize_graph_snapshot


class GraphStep4Tests(unittest.TestCase):
    def _snapshot(self, repo="repo", revision="rev", snapshot_id="snap"):
        node = GraphNode.create(repo, NodeKind.FUNCTION, "run", "pkg.run", "main.py", "python", revision, ("main.py:1",))
        edge = GraphEdge.create(repo, EdgeKind.CALLS, node.node_id, node.node_id, 1.0, ("main.py:2",))
        return GraphSnapshot(snapshot_id, repo, revision, (node,), (edge,))

    def test_save_load_preserves_empty_and_populated_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            store = GraphStore(directory)
            empty = self._snapshot(snapshot_id="empty")
            populated = self._snapshot()
            store.save(empty)
            store.save(populated)
            self.assertEqual(store.load("repo", "empty"), empty)
            loaded = store.load("repo", "snap")
            self.assertEqual(loaded, populated)
            self.assertEqual(loaded.nodes[0].provenance, ("main.py:1",))
            self.assertEqual(loaded.edges[0].provenance, ("main.py:2",))
            self.assertEqual(serialize_graph_snapshot(loaded), serialize_graph_snapshot(populated))

    def test_publish_and_reload_current_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            store = GraphStore(Path(directory))
            first = self._snapshot(revision="one", snapshot_id="first")
            second = self._snapshot(revision="two", snapshot_id="second")
            store.publish(first)
            self.assertEqual(store.load_current("repo"), first)
            store.publish(second)
            self.assertEqual(store.load_current("repo"), second)
            self.assertEqual(store.load("repo", "first"), first)

    def test_identity_isolation_and_missing_or_corrupt_data(self):
        with tempfile.TemporaryDirectory() as directory:
            store = GraphStore(directory)
            store.save(self._snapshot())
            with self.assertRaises(FileNotFoundError):
                store.load("other", "snap")
            with self.assertRaises(FileNotFoundError):
                store.load_current("other")
            files = list((Path(directory) / "snapshots").glob("*.json"))
            files[0].write_text("not-json", encoding="utf-8")
            with self.assertRaises(ValueError):
                store.load("repo", "snap")

    def test_repeated_persistence_is_deterministic_and_input_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            store = GraphStore(directory)
            snapshot = self._snapshot()
            before = serialize_graph_snapshot(snapshot)
            store.save(snapshot)
            first = (Path(directory) / "snapshots").glob("*.json")
            first_bytes = next(first).read_bytes()
            store.save(snapshot)
            second_bytes = next((Path(directory) / "snapshots").glob("*.json")).read_bytes()
            self.assertEqual(first_bytes, second_bytes)
            self.assertEqual(serialize_graph_snapshot(snapshot), before)


if __name__ == "__main__":
    unittest.main()
