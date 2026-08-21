import unittest

from qwen3_coder_next.graph import EdgeKind, GraphEdge, GraphNode, GraphQuery, GraphSnapshot, GraphTraversalService, NodeKind, QueryDirection


class GraphStep5Tests(unittest.TestCase):
    def setUp(self):
        self.a = GraphNode.create("repo", NodeKind.FUNCTION, "a", "a", "a.py", "python", "r")
        self.b = GraphNode.create("repo", NodeKind.FUNCTION, "b", "b", "b.py", "python", "r")
        self.c = GraphNode.create("repo", NodeKind.FUNCTION, "c", "c", "c.py", "python", "r")
        self.d = GraphNode.create("repo", NodeKind.CLASS, "d", "d", "d.py", "python", "r")
        self.edges = (
            GraphEdge.create("repo", EdgeKind.CALLS, self.a.node_id, self.b.node_id, 1.0),
            GraphEdge.create("repo", EdgeKind.CALLS, self.a.node_id, self.c.node_id, 1.0),
            GraphEdge.create("repo", EdgeKind.DEFINES, self.b.node_id, self.d.node_id, 1.0),
            GraphEdge.create("repo", EdgeKind.CALLS, self.c.node_id, self.d.node_id, 1.0),
            GraphEdge.create("repo", EdgeKind.CALLS, self.d.node_id, self.a.node_id, 1.0),
        )
        self.snapshot = GraphSnapshot("snap", "repo", "r", (self.d, self.c, self.b, self.a), self.edges)
        self.service = GraphTraversalService()

    def test_forward_depth_and_edge_filter(self):
        result = self.service.execute(self.snapshot, self.a.node_id, GraphQuery("repo", "r", depth=2, direction="outgoing", edge_filters=("calls",)))
        self.assertEqual(result.root_nodes, (self.a.node_id,))
        self.assertEqual(set(node.node_id for node in result.nodes), {self.a.node_id, self.b.node_id, self.c.node_id, self.d.node_id})
        self.assertEqual(dict(result.traversal_metadata.depths)[self.a.node_id], 0)
        self.assertTrue(all(edge.kind == EdgeKind.CALLS for edge in result.edges))

    def test_reverse_and_node_filter(self):
        result = self.service.execute(self.snapshot, self.d.node_id, GraphQuery("repo", "r", depth=1, direction=QueryDirection.INCOMING, node_filters=("function",)))
        self.assertIn(self.d.node_id, result.root_nodes)
        self.assertEqual({node.node_id for node in result.nodes}, {self.b.node_id, self.c.node_id, self.d.node_id})

    def test_diamond_deduplication_cycle_termination_and_repeatability(self):
        query = GraphQuery("repo", "r", depth=10, direction="outgoing")
        first = self.service.execute(self.snapshot, self.a.node_id, query)
        second = self.service.execute(self.snapshot, self.a.node_id, query)
        self.assertEqual(first, second)
        self.assertEqual(len({node.node_id for node in first.nodes}), len(first.nodes))
        self.assertEqual(len({edge.edge_id for edge in first.edges}), len(first.edges))

    def test_missing_empty_and_invalid_queries(self):
        with self.assertRaises(KeyError):
            self.service.execute(self.snapshot, "missing", GraphQuery("repo", "r"))
        empty = GraphSnapshot("empty", "repo", "r")
        with self.assertRaises(KeyError):
            self.service.execute(empty, "missing", GraphQuery("repo", "r"))
        with self.assertRaises(ValueError):
            self.service.execute(self.snapshot, self.a.node_id, GraphQuery("other", "r"))
        with self.assertRaises(ValueError):
            self.service.execute(self.snapshot, self.a.node_id, GraphQuery("repo", "r", depth=-1))

    def test_result_limit_is_enforced_deterministically(self):
        result = self.service.execute(self.snapshot, self.a.node_id, GraphQuery("repo", "r", depth=10, limit=2))
        self.assertEqual(len(result.nodes), 2)
        self.assertEqual(result.nodes[0].node_id, self.a.node_id)
        self.assertEqual(tuple(node.node_id for node in result.nodes[1:]), tuple(sorted(node.node_id for node in result.nodes[1:])))


if __name__ == "__main__":
    unittest.main()
