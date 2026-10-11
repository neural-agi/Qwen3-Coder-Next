import unittest

from qwen3_coder_next.graph import EdgeKind, GraphEdge, GraphExporter, GraphNode, GraphQuery, GraphSnapshot, GraphTraversalService, NodeKind


class GraphStep7Tests(unittest.TestCase):
    def test_json_csv_and_text_exports_are_deterministic(self):
        node = GraphNode.create("repo", NodeKind.FUNCTION, "run", "run", "main.py", "python", "r")
        edge = GraphEdge.create("repo", EdgeKind.CALLS, node.node_id, node.node_id, 1.0, ("main.py:1",))
        snapshot = GraphSnapshot("s", "repo", "r", (node,), (edge,))
        exporter = GraphExporter()
        self.assertEqual(exporter.to_json(snapshot), exporter.to_json(snapshot))
        self.assertIn("NODE", exporter.to_text(snapshot))
        self.assertIn("EDGE", exporter.to_text(snapshot))
        csv_output = exporter.to_csv(snapshot)
        self.assertIn("record_type,id,kind,source,target,path,revision_id", csv_output)
        self.assertIn(node.node_id, csv_output)
        self.assertIn(edge.edge_id, csv_output)

    def test_invalid_export_input_is_rejected(self):
        with self.assertRaises(ValueError):
            GraphExporter().to_json("bad")  # type: ignore[arg-type]

    def test_export_matches_traversal_subgraph_identity(self):
        first = GraphNode.create("repo", NodeKind.FUNCTION, "first", "first", "a.py", "python", "r")
        second = GraphNode.create("repo", NodeKind.FUNCTION, "second", "second", "b.py", "python", "r")
        edge = GraphEdge.create("repo", EdgeKind.CALLS, first.node_id, second.node_id, 1.0)
        snapshot = GraphSnapshot("s", "repo", "r", (first, second), (edge,))
        result = GraphTraversalService().execute(snapshot, first.node_id, GraphQuery("repo", "r", depth=1, direction="outgoing"))
        subgraph = GraphSnapshot(snapshot.snapshot_id, snapshot.repo_id, snapshot.revision_id, result.nodes, result.edges)
        exported = GraphExporter().to_json(subgraph)
        for node in result.nodes:
            self.assertIn(node.node_id, exported)
        for relationship in result.edges:
            self.assertIn(relationship.edge_id, exported)


if __name__ == "__main__":
    unittest.main()
