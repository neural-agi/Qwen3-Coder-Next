"""Immutable, versioned foundation contracts for the Part 10 graph."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

GRAPH_SCHEMA_VERSION = 1


class NodeKind(str, Enum):
    """Graph entity vocabulary required by the graph foundation."""

    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    VARIABLE = "variable"
    EXTERNAL_DEPENDENCY = "external_dependency"


class EdgeKind(str, Enum):
    """Typed relationships supported by the graph foundation."""

    IMPORTS = "imports"
    CALLS = "calls"
    DEFINES = "defines"
    REFERENCES = "references"
    CONTAINS = "contains"
    DEPENDS_ON = "depends_on"


class QueryDirection(str, Enum):
    """Direction for later graph traversal consumers."""

    OUTGOING = "outgoing"
    INCOMING = "incoming"
    BOTH = "both"


def _text(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f"{name} must be non-empty text.")
    return value if allow_empty else value.strip()


def _texts(value: object, name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must be a collection of text.")
    try:
        values = tuple(value or ())  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValueError(f"{name} must be a collection of text.") from exc
    if any(not isinstance(item, str) or not item.strip() for item in values):
        raise ValueError(f"{name} contains invalid text.")
    return tuple(sorted({item.strip() for item in values}))


def canonical_graph_id(repository_id: str, language: str, symbol_path: str) -> str:
    """Return a stable ID for one repository-scoped language symbol path."""
    repository = _text(repository_id, "repository_id")
    language_value = _text(language, "language").lower()
    symbol = _text(symbol_path, "symbol_path").replace("\\", "/")
    payload = {"repository_id": repository, "language": language_value, "symbol_path": symbol}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "graph:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def canonical_edge_id(repository_id: str, kind: EdgeKind | str, from_node: str, to_node: str) -> str:
    """Return a stable ID for one typed relationship."""
    payload = {
        "repository_id": _text(repository_id, "repository_id"),
        "kind": _text(kind.value if isinstance(kind, EdgeKind) else kind, "kind"),
        "from_node": _text(from_node, "from_node"),
        "to_node": _text(to_node, "to_node"),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "edge:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class SourceUnit:
    """Repository file input for graph extraction stages."""

    repo_id: str
    path: str
    language: str
    file_hash: str
    revision_id: str
    schema_version: int = GRAPH_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("repo_id", "path", "language", "file_hash", "revision_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "path", self.path.replace("\\", "/"))

    def to_dict(self) -> dict[str, Any]:
        return {"repo_id": self.repo_id, "path": self.path, "language": self.language, "file_hash": self.file_hash, "revision_id": self.revision_id, "schema_version": self.schema_version}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceUnit":
        if not isinstance(payload, dict):
            raise ValueError("source unit payload must be a mapping.")
        return cls(payload["repo_id"], payload["path"], payload["language"], payload["file_hash"], payload["revision_id"], int(payload.get("schema_version", GRAPH_SCHEMA_VERSION)))


@dataclass(frozen=True, slots=True)
class GraphNode:
    """Canonical graph entity with source provenance."""

    node_id: str
    kind: NodeKind
    name: str
    qualified_name: str
    file_path: str
    language: str
    revision_id: str
    provenance: tuple[str, ...] = ()
    schema_version: int = GRAPH_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", _text(self.node_id, "node_id"))
        object.__setattr__(self, "kind", self.kind if isinstance(self.kind, NodeKind) else NodeKind(self.kind))
        for name in ("name", "qualified_name", "file_path", "language", "revision_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "file_path", self.file_path.replace("\\", "/"))
        object.__setattr__(self, "provenance", _texts(self.provenance, "provenance"))

    @classmethod
    def create(cls, repository_id: str, kind: NodeKind | str, name: str, qualified_name: str, file_path: str, language: str, revision_id: str, provenance: tuple[str, ...] = ()) -> "GraphNode":
        return cls(canonical_graph_id(repository_id, language, qualified_name), kind, name, qualified_name, file_path, language, revision_id, provenance)

    def to_dict(self) -> dict[str, Any]:
        return {"node_id": self.node_id, "kind": self.kind.value, "name": self.name, "qualified_name": self.qualified_name, "file_path": self.file_path, "language": self.language, "revision_id": self.revision_id, "provenance": list(self.provenance), "schema_version": self.schema_version}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GraphNode":
        if not isinstance(payload, dict):
            raise ValueError("graph node payload must be a mapping.")
        return cls(payload["node_id"], NodeKind(payload["kind"]), payload["name"], payload["qualified_name"], payload["file_path"], payload["language"], payload["revision_id"], tuple(payload.get("provenance", ())), int(payload.get("schema_version", GRAPH_SCHEMA_VERSION)))


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """Canonical typed relationship preserving its evidence provenance."""

    edge_id: str
    kind: EdgeKind
    from_node: str
    to_node: str
    confidence: float
    provenance: tuple[str, ...] = ()
    schema_version: int = GRAPH_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "edge_id", _text(self.edge_id, "edge_id"))
        object.__setattr__(self, "kind", self.kind if isinstance(self.kind, EdgeKind) else EdgeKind(self.kind))
        for name in ("from_node", "to_node"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if not isinstance(self.confidence, (int, float)) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1.")
        object.__setattr__(self, "provenance", _texts(self.provenance, "provenance"))

    @classmethod
    def create(cls, repository_id: str, kind: EdgeKind | str, from_node: str, to_node: str, confidence: float, provenance: tuple[str, ...] = ()) -> "GraphEdge":
        return cls(canonical_edge_id(repository_id, kind, from_node, to_node), kind, from_node, to_node, confidence, provenance)

    def to_dict(self) -> dict[str, Any]:
        return {"edge_id": self.edge_id, "kind": self.kind.value, "from_node": self.from_node, "to_node": self.to_node, "confidence": self.confidence, "provenance": list(self.provenance), "schema_version": self.schema_version}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GraphEdge":
        if not isinstance(payload, dict):
            raise ValueError("graph edge payload must be a mapping.")
        return cls(payload["edge_id"], EdgeKind(payload["kind"]), payload["from_node"], payload["to_node"], float(payload["confidence"]), tuple(payload.get("provenance", ())), int(payload.get("schema_version", GRAPH_SCHEMA_VERSION)))


@dataclass(frozen=True, slots=True)
class GraphSnapshot:
    """Immutable graph state at one repository revision."""

    snapshot_id: str
    repo_id: str
    revision_id: str
    nodes: tuple[GraphNode, ...] = field(default_factory=tuple)
    edges: tuple[GraphEdge, ...] = field(default_factory=tuple)
    schema_version: int = GRAPH_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("snapshot_id", "repo_id", "revision_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if any(not isinstance(node, GraphNode) for node in self.nodes):
            raise ValueError("nodes contains an invalid graph node.")
        if any(not isinstance(edge, GraphEdge) for edge in self.edges):
            raise ValueError("edges contains an invalid graph edge.")
        nodes = tuple(sorted(self.nodes, key=lambda item: item.node_id))
        edges = tuple(sorted(self.edges, key=lambda item: item.edge_id))
        if len({item.node_id for item in nodes}) != len(nodes):
            raise ValueError("nodes contain duplicate canonical IDs.")
        if len({item.edge_id for item in edges}) != len(edges):
            raise ValueError("edges contain duplicate canonical IDs.")
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)

    def to_dict(self) -> dict[str, Any]:
        return {"snapshot_id": self.snapshot_id, "repo_id": self.repo_id, "revision_id": self.revision_id, "nodes": [node.to_dict() for node in self.nodes], "edges": [edge.to_dict() for edge in self.edges], "schema_version": self.schema_version}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GraphSnapshot":
        if not isinstance(payload, dict):
            raise ValueError("graph snapshot payload must be a mapping.")
        return cls(payload["snapshot_id"], payload["repo_id"], payload["revision_id"], tuple(GraphNode.from_dict(item) for item in payload.get("nodes", ())), tuple(GraphEdge.from_dict(item) for item in payload.get("edges", ())), int(payload.get("schema_version", GRAPH_SCHEMA_VERSION)))


@dataclass(frozen=True, slots=True)
class GraphQuery:
    """Structured query request for later traversal/query stages."""

    repo_id: str
    revision_id: str
    node_filters: tuple[str, ...] = ()
    edge_filters: tuple[EdgeKind, ...] = ()
    depth: int = 1
    direction: QueryDirection = QueryDirection.BOTH
    limit: int = 100
    scope: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "repo_id", _text(self.repo_id, "repo_id"))
        object.__setattr__(self, "revision_id", _text(self.revision_id, "revision_id"))
        object.__setattr__(self, "node_filters", _texts(self.node_filters, "node_filters"))
        edge_filters = tuple(item if isinstance(item, EdgeKind) else EdgeKind(item) for item in self.edge_filters)
        object.__setattr__(self, "edge_filters", tuple(sorted(set(edge_filters), key=lambda item: item.value)))
        if not isinstance(self.depth, int) or self.depth < 0:
            raise ValueError("depth must be a non-negative integer.")
        object.__setattr__(self, "direction", self.direction if isinstance(self.direction, QueryDirection) else QueryDirection(self.direction))
        if not isinstance(self.limit, int) or self.limit <= 0:
            raise ValueError("limit must be a positive integer.")
        object.__setattr__(self, "scope", _text(self.scope, "scope", allow_empty=True))

    def to_dict(self) -> dict[str, Any]:
        return {"repo_id": self.repo_id, "revision_id": self.revision_id, "node_filters": list(self.node_filters), "edge_filters": [item.value for item in self.edge_filters], "depth": self.depth, "direction": self.direction.value, "limit": self.limit, "scope": self.scope, "schema_version": GRAPH_SCHEMA_VERSION}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GraphQuery":
        if not isinstance(payload, dict):
            raise ValueError("graph query payload must be a mapping.")
        return cls(payload["repo_id"], payload["revision_id"], tuple(payload.get("node_filters", ())), tuple(payload.get("edge_filters", ())), int(payload.get("depth", 1)), payload.get("direction", QueryDirection.BOTH.value), int(payload.get("limit", 100)), payload.get("scope", ""))
