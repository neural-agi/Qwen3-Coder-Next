"""Deterministic graph invalidation for changed paths and renamed symbols."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from qwen3_coder_next.graph.schemas import GraphEdge, GraphNode, GraphSnapshot


@dataclass(frozen=True, slots=True)
class InvalidationEvent:
    repo_id: str
    touched_paths: tuple[str, ...] = ()
    renamed_symbols: tuple[str, ...] = ()
    revision_id: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.repo_id, str) or not self.repo_id.strip():
            raise ValueError("repo_id must be non-empty text.")
        if isinstance(self.touched_paths, (str, bytes)) or isinstance(self.renamed_symbols, (str, bytes)):
            raise ValueError("invalidation collections must be text collections.")
        object.__setattr__(self, "repo_id", self.repo_id.strip())
        object.__setattr__(self, "touched_paths", tuple(sorted({str(item).replace("\\", "/").strip("/") for item in self.touched_paths if str(item).strip()})))
        object.__setattr__(self, "renamed_symbols", tuple(sorted({str(item).strip() for item in self.renamed_symbols if str(item).strip()})))
        if not isinstance(self.revision_id, str) or not self.revision_id.strip():
            raise ValueError("revision_id must be non-empty text.")
        object.__setattr__(self, "revision_id", self.revision_id.strip())


@dataclass(frozen=True, slots=True)
class InvalidationResult:
    snapshot: GraphSnapshot
    stale_node_ids: tuple[str, ...] = ()
    stale_edge_ids: tuple[str, ...] = ()
    dirty_paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RebuildInput:
    """Canonical replacement records supplied by a later rebuild boundary."""

    nodes: tuple[GraphNode, ...] = field(default_factory=tuple)
    edges: tuple[GraphEdge, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        nodes = tuple(self.nodes)
        edges = tuple(self.edges)
        if any(not isinstance(node, GraphNode) for node in nodes):
            raise ValueError("nodes contains an invalid GraphNode.")
        if any(not isinstance(edge, GraphEdge) for edge in edges):
            raise ValueError("edges contains an invalid GraphEdge.")
        if len({node.node_id for node in nodes}) != len(nodes):
            raise ValueError("replacement nodes contain duplicate IDs.")
        if len({edge.edge_id for edge in edges}) != len(edges):
            raise ValueError("replacement edges contain duplicate IDs.")
        object.__setattr__(self, "nodes", tuple(sorted(nodes, key=lambda item: item.node_id)))
        object.__setattr__(self, "edges", tuple(sorted(edges, key=lambda item: item.edge_id)))


class InvalidationManager:
    """Create a new snapshot with stale graph regions removed."""

    def invalidate(self, snapshot: GraphSnapshot, event: InvalidationEvent) -> InvalidationResult:
        return self.reconcile(snapshot, event, RebuildInput())

    def reconcile(self, snapshot: GraphSnapshot, event: InvalidationEvent, rebuild: RebuildInput) -> InvalidationResult:
        if not isinstance(snapshot, GraphSnapshot):
            raise ValueError("snapshot must be a GraphSnapshot.")
        if not isinstance(event, InvalidationEvent):
            raise ValueError("event must be an InvalidationEvent.")
        if not isinstance(rebuild, RebuildInput):
            raise ValueError("rebuild must be a RebuildInput.")
        if event.repo_id != snapshot.repo_id:
            raise ValueError("event repository must match the snapshot.")
        stale_nodes = tuple(sorted(node.node_id for node in snapshot.nodes if self._stale_node(node, event)))
        stale_set = set(stale_nodes)
        stale_edges = tuple(sorted(edge.edge_id for edge in snapshot.edges if edge.from_node in stale_set or edge.to_node in stale_set))
        remaining_nodes = tuple(node for node in snapshot.nodes if node.node_id not in stale_set)
        remaining_edges = tuple(edge for edge in snapshot.edges if edge.edge_id not in set(stale_edges))
        existing_node_ids = {node.node_id for node in remaining_nodes}
        existing_edge_ids = {edge.edge_id for edge in remaining_edges}
        if existing_node_ids.intersection(node.node_id for node in rebuild.nodes):
            raise ValueError("replacement nodes duplicate unaffected node IDs.")
        if existing_edge_ids.intersection(edge.edge_id for edge in rebuild.edges):
            raise ValueError("replacement edges duplicate unaffected edge IDs.")
        combined_nodes = remaining_nodes + rebuild.nodes
        combined_node_ids = {node.node_id for node in combined_nodes}
        if any(edge.from_node not in combined_node_ids or edge.to_node not in combined_node_ids for edge in rebuild.edges):
            raise ValueError("replacement edges must reference combined graph nodes.")
        combined_edges = remaining_edges + rebuild.edges
        snapshot_id = self._snapshot_id(snapshot.repo_id, event.revision_id, combined_nodes, combined_edges)
        updated = GraphSnapshot(snapshot_id, snapshot.repo_id, event.revision_id, combined_nodes, combined_edges, snapshot.schema_version)
        return InvalidationResult(updated, stale_nodes, stale_edges, event.touched_paths)

    @staticmethod
    def _stale_node(node: GraphNode, event: InvalidationEvent) -> bool:
        return node.file_path in event.touched_paths or node.qualified_name in event.renamed_symbols or node.name in event.renamed_symbols

    @staticmethod
    def _snapshot_id(repo_id: str, revision_id: str, nodes: tuple[GraphNode, ...], edges: tuple[GraphEdge, ...]) -> str:
        payload = {"repo_id": repo_id, "revision_id": revision_id, "nodes": [node.to_dict() for node in nodes], "edges": [edge.to_dict() for edge in edges]}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return "snapshot:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()
