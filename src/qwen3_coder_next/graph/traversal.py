"""Deterministic, read-only traversal over canonical graph snapshots."""
from __future__ import annotations

from dataclasses import dataclass, field

from qwen3_coder_next.graph.schemas import EdgeKind, GraphEdge, GraphNode, GraphQuery, GraphSnapshot, QueryDirection


@dataclass(frozen=True, slots=True)
class TraversalMetadata:
    """Bounded traversal metadata preserving node depth and query identity."""

    depths: tuple[tuple[str, int], ...] = ()
    direction: QueryDirection = QueryDirection.BOTH


@dataclass(frozen=True, slots=True)
class TraversalResult:
    """Immutable subgraph result returned by the traversal boundary."""

    nodes: tuple[GraphNode, ...] = field(default_factory=tuple)
    edges: tuple[GraphEdge, ...] = field(default_factory=tuple)
    root_nodes: tuple[str, ...] = ()
    traversal_metadata: TraversalMetadata = field(default_factory=TraversalMetadata)


class GraphTraversalService:
    """Execute bounded deterministic graph traversals without mutating snapshots."""

    def execute(self, snapshot: GraphSnapshot, start_node: str, query: GraphQuery) -> TraversalResult:
        if not isinstance(snapshot, GraphSnapshot):
            raise ValueError("snapshot must be a GraphSnapshot.")
        if not isinstance(query, GraphQuery):
            raise ValueError("query must be a GraphQuery.")
        if query.repo_id != snapshot.repo_id or query.revision_id != snapshot.revision_id:
            raise ValueError("query repository and revision must match the snapshot.")
        if not isinstance(start_node, str) or not start_node.strip():
            raise ValueError("start_node must be non-empty text.")
        start_node = start_node.strip()
        nodes = {node.node_id: node for node in snapshot.nodes}
        if start_node not in nodes:
            raise KeyError(start_node)
        edges = tuple(sorted(snapshot.edges, key=lambda item: item.edge_id))
        edge_kinds = set(query.edge_filters)
        adjacency: dict[str, list[tuple[str, GraphEdge]]] = {node_id: [] for node_id in nodes}
        for edge in edges:
            if edge.kind not in edge_kinds if edge_kinds else False:
                continue
            if query.direction in {QueryDirection.OUTGOING, QueryDirection.BOTH}:
                adjacency[edge.from_node].append((edge.to_node, edge))
            if query.direction in {QueryDirection.INCOMING, QueryDirection.BOTH}:
                adjacency[edge.to_node].append((edge.from_node, edge))
        distances = {start_node: 0}
        queue = [start_node]
        reached_edges: dict[str, GraphEdge] = {}
        while queue:
            current = queue.pop(0)
            if distances[current] >= query.depth:
                continue
            for target, edge in sorted(adjacency[current], key=lambda item: (item[1].edge_id, item[0])):
                reached_edges[edge.edge_id] = edge
                if target not in distances:
                    distances[target] = distances[current] + 1
                    queue.append(target)
        selected_ids = {node_id for node_id in distances if self._matches(nodes[node_id], query.node_filters)}
        selected_ids.add(start_node)
        ordered_ids = (start_node,) + tuple(sorted(selected_ids - {start_node}))[: max(0, query.limit - 1)]
        selected_ids = set(ordered_ids)
        selected_nodes = tuple(nodes[node_id] for node_id in ordered_ids)
        selected_edges = tuple(sorted((edge for edge in reached_edges.values() if edge.from_node in selected_ids and edge.to_node in selected_ids), key=lambda item: item.edge_id))
        metadata = TraversalMetadata(tuple(sorted(distances.items())), query.direction)
        return TraversalResult(selected_nodes, selected_edges, (start_node,), metadata)

    @staticmethod
    def _matches(node: GraphNode, filters: tuple[str, ...]) -> bool:
        if not filters:
            return True
        values = {node.node_id, node.kind.value, node.name, node.qualified_name, node.file_path, node.language}
        return any(item in values for item in filters)
