"""Explicit consistency checks for immutable graph snapshots."""
from __future__ import annotations

from qwen3_coder_next.graph.schemas import GraphSnapshot


class GraphConsistencyValidator:
    """Validate canonical IDs and endpoint consistency without mutating a snapshot."""

    def validate(self, snapshot: GraphSnapshot) -> None:
        if not isinstance(snapshot, GraphSnapshot):
            raise ValueError("snapshot must be a GraphSnapshot.")
        node_ids = [node.node_id for node in snapshot.nodes]
        edge_ids = [edge.edge_id for edge in snapshot.edges]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("graph snapshot contains duplicate node IDs.")
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("graph snapshot contains duplicate edge IDs.")
        known_nodes = set(node_ids)
        if any(edge.from_node not in known_nodes or edge.to_node not in known_nodes for edge in snapshot.edges):
            raise ValueError("graph snapshot contains an edge with a missing endpoint.")
