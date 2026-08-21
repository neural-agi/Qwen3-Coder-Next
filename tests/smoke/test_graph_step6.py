import unittest

from qwen3_coder_next.graph import EdgeKind, GraphEdge, GraphNode, GraphSnapshot, InvalidationEvent, InvalidationManager, NodeKind, RebuildInput


class GraphStep6Tests(unittest.TestCase):
    def test_partial_invalidation_preserves_unaffected_region(self):
        a = GraphNode.create("repo", NodeKind.FUNCTION, "a", "a", "a.py", "python", "r1")
        b = GraphNode.create("repo", NodeKind.FUNCTION, "b", "b", "b.py", "python", "r1")
        edge = GraphEdge.create("repo", EdgeKind.CALLS, a.node_id, b.node_id, 1.0)
        snapshot = GraphSnapshot("s1", "repo", "r1", (a, b), (edge,))
        result = InvalidationManager().invalidate(snapshot, InvalidationEvent("repo", ("a.py",), revision_id="r2"))
        self.assertEqual(result.stale_node_ids, (a.node_id,))
        self.assertEqual(result.stale_edge_ids, (edge.edge_id,))
        self.assertEqual(result.snapshot.nodes, (b,))
        self.assertEqual(result.snapshot.edges, ())
        self.assertEqual(result.snapshot.revision_id, "r2")

    def test_rename_and_empty_invalidation_are_deterministic(self):
        node = GraphNode.create("repo", NodeKind.FUNCTION, "run", "pkg.run", "main.py", "python", "r1")
        snapshot = GraphSnapshot("s1", "repo", "r1", (node,), ())
        manager = InvalidationManager()
        renamed = manager.invalidate(snapshot, InvalidationEvent("repo", renamed_symbols=("pkg.run",), revision_id="r2"))
        self.assertEqual(renamed.stale_node_ids, (node.node_id,))
        first = manager.invalidate(snapshot, InvalidationEvent("repo", revision_id="r2"))
        second = manager.invalidate(snapshot, InvalidationEvent("repo", revision_id="r2"))
        self.assertEqual(first, second)
        self.assertEqual(first.snapshot.nodes, (node,))

    def test_reconcile_replaces_stale_region_and_preserves_unaffected_records(self):
        old = GraphNode.create("repo", NodeKind.FUNCTION, "old", "old", "changed.py", "python", "r1")
        stable = GraphNode.create("repo", NodeKind.FUNCTION, "stable", "stable", "stable.py", "python", "r1")
        replacement = GraphNode.create("repo", NodeKind.FUNCTION, "new", "new", "changed.py", "python", "r2")
        original = GraphSnapshot("s1", "repo", "r1", (old, stable), ())
        result = InvalidationManager().reconcile(original, InvalidationEvent("repo", ("changed.py",), revision_id="r2"), RebuildInput((replacement,), ()))
        self.assertEqual(result.snapshot.nodes, tuple(sorted((stable, replacement), key=lambda item: item.node_id)))
        self.assertEqual(original.nodes, tuple(sorted((old, stable), key=lambda item: item.node_id)))
        self.assertEqual(result.snapshot.revision_id, "r2")

    def test_reconcile_rejects_invalid_replacements(self):
        node = GraphNode.create("repo", NodeKind.FUNCTION, "node", "node", "a.py", "python", "r1")
        original = GraphSnapshot("s", "repo", "r1", (node,), ())
        with self.assertRaises(ValueError):
            InvalidationManager().reconcile(original, InvalidationEvent("repo", ("a.py",), revision_id="r2"), RebuildInput((), (GraphEdge.create("repo", EdgeKind.CALLS, "missing", "missing2", 1.0),)))

    def test_reconcile_reconciles_incident_edges_and_supports_deletion(self):
        changed = GraphNode.create("repo", NodeKind.FUNCTION, "changed", "changed", "changed.py", "python", "r1")
        stable = GraphNode.create("repo", NodeKind.FUNCTION, "stable", "stable", "stable.py", "python", "r1")
        old_edge = GraphEdge.create("repo", EdgeKind.CALLS, changed.node_id, stable.node_id, 1.0)
        original = GraphSnapshot("s", "repo", "r1", (changed, stable), (old_edge,))
        replacement = GraphNode.create("repo", NodeKind.FUNCTION, "renamed", "renamed", "changed.py", "python", "r2")
        new_edge = GraphEdge.create("repo", EdgeKind.CALLS, replacement.node_id, stable.node_id, 1.0)
        manager = InvalidationManager()
        rebuilt = manager.reconcile(original, InvalidationEvent("repo", ("changed.py",), revision_id="r2"), RebuildInput([replacement], [new_edge]))
        self.assertEqual(rebuilt.snapshot.nodes, tuple(sorted((stable, replacement), key=lambda item: item.node_id)))
        self.assertEqual(rebuilt.snapshot.edges, (new_edge,))
        deleted = manager.reconcile(original, InvalidationEvent("repo", ("changed.py",), revision_id="r3"), RebuildInput())
        self.assertEqual(deleted.snapshot.nodes, (stable,))
        self.assertEqual(deleted.snapshot.edges, ())

    def test_reconcile_rejects_duplicate_or_unrelated_replacement_records(self):
        node = GraphNode.create("repo", NodeKind.FUNCTION, "node", "node", "a.py", "python", "r1")
        stable = GraphNode.create("repo", NodeKind.FUNCTION, "stable", "stable", "stable.py", "python", "r1")
        original = GraphSnapshot("s", "repo", "r1", (node, stable), ())
        event = InvalidationEvent("repo", ("a.py",), revision_id="r2")
        manager = InvalidationManager()
        with self.assertRaises(ValueError):
            manager.reconcile(original, event, RebuildInput((stable,), ()))
        duplicate = GraphNode.create("repo", NodeKind.FUNCTION, "node", "node", "a.py", "python", "r2")
        with self.assertRaises(ValueError):
            manager.reconcile(original, event, RebuildInput((duplicate, duplicate), ()))

    def test_reconcile_replay_is_deterministic_and_preserves_revision(self):
        old = GraphNode.create("repo", NodeKind.FUNCTION, "old", "old", "a.py", "python", "r1")
        stable = GraphNode.create("repo", NodeKind.FUNCTION, "stable", "stable", "b.py", "python", "r1")
        replacement = GraphNode.create("repo", NodeKind.FUNCTION, "new", "new", "a.py", "python", "r2")
        original = GraphSnapshot("s", "repo", "r1", (old, stable), ())
        event = InvalidationEvent("repo", ("a.py",), revision_id="r2")
        manager = InvalidationManager()
        first = manager.reconcile(original, event, RebuildInput((replacement,), ()))
        second = manager.reconcile(original, event, RebuildInput((replacement,), ()))
        self.assertEqual(first, second)
        self.assertEqual(first.snapshot.revision_id, "r2")
        self.assertEqual(first.snapshot.schema_version, original.schema_version)

    def test_invalid_events_are_rejected(self):
        snapshot = GraphSnapshot("s", "repo", "r", (), ())
        with self.assertRaises(ValueError):
            InvalidationManager().invalidate(snapshot, InvalidationEvent("other", revision_id="r2"))


if __name__ == "__main__":
    unittest.main()
