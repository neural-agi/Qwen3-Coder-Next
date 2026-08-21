import unittest
from dataclasses import FrozenInstanceError

from qwen3_coder_next.graph import (
    EdgeKind,
    GraphEdge,
    GraphNode,
    GraphQuery,
    GraphSnapshot,
    NodeKind,
    QueryDirection,
    SourceUnit,
    canonical_graph_id,
    deserialize_graph_snapshot,
    serialize_graph_snapshot,
)


class GraphStep1Tests(unittest.TestCase):
    def test_source_unit_and_node_identity_are_deterministic(self):
        source = SourceUnit("repo", "src/main.py", "Python", "hash", "rev-1")
        self.assertEqual(source.path, "src/main.py")
        first = canonical_graph_id("repo", "Python", "pkg.main.run")
        second = canonical_graph_id("repo", "Python", "pkg.main.run")
        self.assertEqual(first, second)
        self.assertNotEqual(first, canonical_graph_id("other", "Python", "pkg.main.run"))
        self.assertNotEqual(first, canonical_graph_id("repo", "Python", "pkg.main.stop"))
        node = GraphNode.create("repo", NodeKind.FUNCTION, "run", "pkg.main.run", "src/main.py", "Python", "rev-1", ("line:1",))
        self.assertEqual(node.node_id, first)
        self.assertEqual(source.to_dict()["language"], "Python")

    def test_edges_and_snapshot_are_sorted_and_immutable(self):
        node_a = GraphNode.create("repo", "function", "a", "a", "a.py", "python", "r")
        node_b = GraphNode.create("repo", "function", "b", "b", "b.py", "python", "r")
        edge = GraphEdge.create("repo", EdgeKind.CALLS, node_a.node_id, node_b.node_id, 0.5, ("a.py:1",))
        snapshot = GraphSnapshot("snap", "repo", "r", (node_b, node_a), (edge,))
        self.assertEqual(tuple(node.node_id for node in snapshot.nodes), tuple(sorted((node_a.node_id, node_b.node_id))))
        self.assertEqual(serialize_graph_snapshot(snapshot), serialize_graph_snapshot(deserialize_graph_snapshot(serialize_graph_snapshot(snapshot))))
        with self.assertRaises(FrozenInstanceError):
            snapshot.nodes += (node_a,)  # type: ignore[misc]

    def test_query_normalizes_filters_and_round_trips(self):
        query = GraphQuery("repo", "r", (" function ", "function"), ("calls", "imports"), depth=0, direction="incoming", limit=5, scope="src")
        self.assertEqual(query.node_filters, ("function",))
        self.assertEqual(query.edge_filters, (EdgeKind.CALLS, EdgeKind.IMPORTS))
        self.assertEqual(query.direction, QueryDirection.INCOMING)
        self.assertEqual(GraphQuery.from_dict(query.to_dict()), query)

    def test_empty_and_malformed_contracts(self):
        snapshot = GraphSnapshot("empty", "repo", "r")
        self.assertEqual(snapshot.nodes, ())
        self.assertEqual(snapshot.edges, ())
        with self.assertRaises(ValueError):
            SourceUnit("", "a.py", "python", "hash", "r")
        with self.assertRaises(ValueError):
            GraphEdge.create("repo", "calls", "a", "b", 2.0)
        with self.assertRaises(ValueError):
            GraphQuery("repo", "r", depth=-1)
        with self.assertRaises(ValueError):
            deserialize_graph_snapshot("not-json")


if __name__ == "__main__":
    unittest.main()
