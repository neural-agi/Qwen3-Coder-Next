"""Deterministic relation normalization and symbol resolution for Part 10 Step 3."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from qwen3_coder_next.graph import EdgeKind, GraphEdge, GraphNode, NodeKind, SourceUnit
from qwen3_coder_next.parsers import FactKind, ParseResult, SyntaxFact


@dataclass(frozen=True, slots=True)
class UnresolvedReference:
    """An import or call that could not be resolved unambiguously."""

    source_path: str
    qualified_name: str
    kind: FactKind
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.kind, FactKind):
            object.__setattr__(self, "kind", FactKind(self.kind))
        for name in ("source_path", "qualified_name"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text.")
            object.__setattr__(self, name, value.strip())
        if isinstance(self.provenance, (str, bytes)):
            raise ValueError("provenance must be a collection of text.")
        object.__setattr__(self, "provenance", tuple(sorted(set(self.provenance))))


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    """Immutable normalized graph facts and explicit unresolved references."""

    nodes: tuple[GraphNode, ...] = field(default_factory=tuple)
    edges: tuple[GraphEdge, ...] = field(default_factory=tuple)
    unresolved: tuple[UnresolvedReference, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if any(not isinstance(item, GraphNode) for item in self.nodes):
            raise ValueError("nodes contains an invalid GraphNode.")
        if any(not isinstance(item, GraphEdge) for item in self.edges):
            raise ValueError("edges contains an invalid GraphEdge.")
        if any(not isinstance(item, UnresolvedReference) for item in self.unresolved):
            raise ValueError("unresolved contains an invalid reference.")
        nodes = tuple(sorted(set(self.nodes), key=lambda item: item.node_id))
        edges = tuple(sorted(set(self.edges), key=lambda item: item.edge_id))
        unresolved = tuple(sorted(set(self.unresolved), key=lambda item: (item.source_path, item.kind.value, item.qualified_name)))
        node_ids = {item.node_id for item in nodes}
        if any(edge.from_node not in node_ids or edge.to_node not in node_ids for edge in edges):
            raise ValueError("edges must reference existing graph nodes.")
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "unresolved", unresolved)


class RelationNormalizer:
    """Normalize parser facts without parsing source text or executing graph behavior."""

    def normalize(self, results: Iterable[ParseResult]) -> NormalizationResult:
        if isinstance(results, (str, bytes)):
            raise ValueError("results must be a collection of ParseResult values.")
        try:
            parsed = tuple(results)
        except TypeError as exc:
            raise ValueError("results must be a collection of ParseResult values.") from exc
        if any(not isinstance(result, ParseResult) for result in parsed):
            raise ValueError("results contains an invalid ParseResult.")
        if not parsed:
            return NormalizationResult()
        units = tuple(sorted(parsed, key=lambda item: (item.source_unit.repo_id, item.source_unit.path, item.source_unit.revision_id)))
        repo_ids = {item.source_unit.repo_id for item in units}
        if len(repo_ids) != 1:
            raise ValueError("all ParseResult values must belong to one repository.")
        repository_id = units[0].source_unit.repo_id
        definitions: dict[tuple[str, str], list[GraphNode]] = {}
        module_by_path: dict[str, GraphNode] = {}
        nodes: dict[str, GraphNode] = {}
        facts_by_path: list[tuple[SourceUnit, SyntaxFact]] = []
        for result in units:
            for fact in result.facts:
                facts_by_path.append((result.source_unit, fact))
                node = self._node_for_fact(repository_id, result.source_unit, fact)
                if node is not None:
                    nodes[node.node_id] = node
                    if fact.kind == FactKind.MODULE:
                        module_by_path[result.source_unit.path] = node
                    elif fact.kind in {FactKind.CLASS, FactKind.FUNCTION, FactKind.VARIABLE}:
                        definitions.setdefault((fact.language.lower(), fact.qualified_name), []).append(node)
        edges: dict[str, GraphEdge] = {}
        unresolved: set[UnresolvedReference] = set()
        for unit, fact in facts_by_path:
            if fact.kind in {FactKind.CLASS, FactKind.FUNCTION, FactKind.VARIABLE}:
                owner = module_by_path.get(unit.path)
                target = next((node for node in nodes.values() if node.file_path == unit.path and node.qualified_name == fact.qualified_name), None)
                if owner is not None and target is not None:
                    edge = GraphEdge.create(repository_id, EdgeKind.DEFINES, owner.node_id, target.node_id, 1.0, fact.provenance)
                    edges[edge.edge_id] = edge
                continue
            if fact.kind not in {FactKind.IMPORT, FactKind.CALL}:
                continue
            owner = module_by_path.get(unit.path)
            if owner is None:
                continue
            targets = definitions.get((fact.language.lower(), fact.qualified_name), [])
            if len(targets) == 1:
                edge_kind = EdgeKind.IMPORTS if fact.kind == FactKind.IMPORT else EdgeKind.CALLS
                edge = GraphEdge.create(repository_id, edge_kind, owner.node_id, targets[0].node_id, 1.0, fact.provenance)
                edges[edge.edge_id] = edge
            elif fact.kind == FactKind.IMPORT:
                external = GraphNode.create(repository_id, NodeKind.EXTERNAL_DEPENDENCY, fact.name, fact.qualified_name, unit.path, fact.language, unit.revision_id, fact.provenance)
                nodes[external.node_id] = external
                edge = GraphEdge.create(repository_id, EdgeKind.IMPORTS, owner.node_id, external.node_id, 0.5, fact.provenance)
                edges[edge.edge_id] = edge
            else:
                unresolved.add(UnresolvedReference(unit.path, fact.qualified_name, fact.kind, fact.provenance))
        return NormalizationResult(tuple(nodes.values()), tuple(edges.values()), tuple(unresolved))

    @staticmethod
    def _node_for_fact(repository_id: str, unit: SourceUnit, fact: SyntaxFact) -> GraphNode | None:
        kinds = {FactKind.MODULE: NodeKind.MODULE, FactKind.CLASS: NodeKind.CLASS, FactKind.FUNCTION: NodeKind.FUNCTION, FactKind.VARIABLE: NodeKind.VARIABLE}
        kind = kinds.get(fact.kind)
        if kind is None:
            return None
        return GraphNode.create(repository_id, kind, fact.name, fact.qualified_name, unit.path, unit.language, unit.revision_id, fact.provenance)
