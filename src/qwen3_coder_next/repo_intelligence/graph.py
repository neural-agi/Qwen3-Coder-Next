"""Repository Intelligence to Code Knowledge Graph integration."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable, Mapping

from qwen3_coder_next.extractors import RelationNormalizer
from qwen3_coder_next.graph import GraphExporter, GraphQuery, GraphSnapshot, GraphStore, GraphTraversalService, SourceUnit
from qwen3_coder_next.parsers import ParseRequest, ParserAdapter, PythonParserAdapter
from qwen3_coder_next.repo_intelligence.schemas import RepoSnapshot


class RepositoryGraphService:
    """Build and consume a graph for one immutable repository snapshot."""

    def __init__(
        self,
        adapters: Mapping[str, ParserAdapter] | None = None,
        normalizer: RelationNormalizer | None = None,
        traversal: GraphTraversalService | None = None,
        exporter: GraphExporter | None = None,
    ) -> None:
        configured = adapters or {PythonParserAdapter.language: PythonParserAdapter()}
        if any(not isinstance(language, str) or not language.strip() or not isinstance(adapter, ParserAdapter) for language, adapter in configured.items()):
            raise ValueError("adapters must map language names to ParserAdapter values.")
        self._adapters = {language.strip().lower(): adapter for language, adapter in configured.items()}
        self._normalizer = normalizer or RelationNormalizer()
        self._traversal = traversal or GraphTraversalService()
        self._exporter = exporter or GraphExporter()

    def build(self, snapshot: RepoSnapshot, *, source_loader: Callable[[Path], str] | None = None) -> GraphSnapshot:
        self._validate_snapshot(snapshot)
        loader = source_loader or self._load_source
        results = []
        root = Path(snapshot.root_path)
        for record in snapshot.files:
            adapter = self._adapters.get(record.language.lower())
            if adapter is None:
                continue
            source_unit = SourceUnit(snapshot.repository_id, record.normalized_path, record.language, record.file_hash, snapshot.snapshot_id)
            request = ParseRequest(source_unit, record.language.lower(), record.normalized_path, snapshot.snapshot_id)
            results.append(adapter.parse(request, loader(root / Path(record.path))))
        normalized = self._normalizer.normalize(results)
        nodes = normalized.nodes
        edges = normalized.edges
        payload = {
            "repo_id": snapshot.repository_id,
            "revision_id": snapshot.snapshot_id,
            "nodes": [node.to_dict() for node in nodes],
            "edges": [edge.to_dict() for edge in edges],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        graph_id = "snapshot:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        return GraphSnapshot(graph_id, snapshot.repository_id, snapshot.snapshot_id, nodes, edges)

    def publish(self, snapshot: RepoSnapshot, store: GraphStore, *, source_loader: Callable[[Path], str] | None = None) -> GraphSnapshot:
        if not isinstance(store, GraphStore):
            raise ValueError("store must be a GraphStore.")
        graph = self.build(snapshot, source_loader=source_loader)
        store.publish(graph)
        return graph

    def query_published(self, store: GraphStore, repository_id: str, start_node: str, query: GraphQuery):
        if not isinstance(store, GraphStore):
            raise ValueError("store must be a GraphStore.")
        graph = store.load_current(repository_id)
        return self._traversal.execute(graph, start_node, query)

    def export_published(self, store: GraphStore, repository_id: str, format_name: str) -> str:
        if not isinstance(store, GraphStore):
            raise ValueError("store must be a GraphStore.")
        graph = store.load_current(repository_id)
        if format_name == "json":
            return self._exporter.to_json(graph)
        if format_name == "csv":
            return self._exporter.to_csv(graph)
        if format_name == "text":
            return self._exporter.to_text(graph)
        raise ValueError("format_name must be json, csv, or text.")

    @staticmethod
    def _validate_snapshot(snapshot: RepoSnapshot) -> None:
        if not isinstance(snapshot, RepoSnapshot):
            raise ValueError("snapshot must be a RepoSnapshot.")
        if not Path(snapshot.root_path).is_dir():
            raise ValueError("snapshot root_path must be an existing directory.")

    @staticmethod
    def _load_source(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ValueError(f"source file could not be read: {path}") from exc
