"""Deterministic graph snapshot export and inspection helpers."""
from __future__ import annotations

import csv
import io

from qwen3_coder_next.graph.schemas import GraphSnapshot
from qwen3_coder_next.graph.serialization import serialize_graph_snapshot


class GraphExporter:
    """Export immutable graph snapshots without accessing storage internals."""

    def to_json(self, snapshot: GraphSnapshot) -> str:
        if not isinstance(snapshot, GraphSnapshot):
            raise ValueError("snapshot must be a GraphSnapshot.")
        return serialize_graph_snapshot(snapshot)

    def to_csv(self, snapshot: GraphSnapshot) -> str:
        if not isinstance(snapshot, GraphSnapshot):
            raise ValueError("snapshot must be a GraphSnapshot.")
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(("record_type", "id", "kind", "source", "target", "path", "revision_id"))
        for node in snapshot.nodes:
            writer.writerow(("node", node.node_id, node.kind.value, "", "", node.file_path, node.revision_id))
        for edge in snapshot.edges:
            writer.writerow(("edge", edge.edge_id, edge.kind.value, edge.from_node, edge.to_node, "", ""))
        return output.getvalue()

    def to_text(self, snapshot: GraphSnapshot) -> str:
        if not isinstance(snapshot, GraphSnapshot):
            raise ValueError("snapshot must be a GraphSnapshot.")
        lines = [f"GraphSnapshot {snapshot.snapshot_id} repo={snapshot.repo_id} revision={snapshot.revision_id}"]
        lines.extend(f"NODE {node.node_id} {node.kind.value} {node.qualified_name} {node.file_path}" for node in snapshot.nodes)
        lines.extend(f"EDGE {edge.edge_id} {edge.kind.value} {edge.from_node} -> {edge.to_node}" for edge in snapshot.edges)
        return "\n".join(lines) + "\n"
