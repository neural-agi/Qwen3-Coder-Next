import unittest

from qwen3_coder_next.graph import EdgeKind, GraphEdge, GraphExporter, GraphNode, GraphSnapshot, NodeKind


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


if __name__ == "__main__":
    unittest.main()
