"""Deterministic retrieval adapters for existing repository, graph, and memory APIs."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Protocol

from qwen3_coder_next.context_compression.schemas import ContextRequest, EvidenceChunk
from qwen3_coder_next.context_compression.source_resolver import SourcePlan, SourcePlanEntry
from qwen3_coder_next.graph import GraphQuery, GraphStore, GraphTraversalService
from qwen3_coder_next.memory import MemoryQuery, MemoryRetriever
from qwen3_coder_next.repo_intelligence.schemas import RepoSnapshot


@dataclass(frozen=True, slots=True)
class RetrievalIssue:
    source_id: str
    status: str
    reason: str


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    chunks: tuple[EvidenceChunk, ...] = field(default_factory=tuple)
    issues: tuple[RetrievalIssue, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if any(not isinstance(item, EvidenceChunk) for item in self.chunks):
            raise ValueError("chunks contains an invalid EvidenceChunk.")
        if any(not isinstance(item, RetrievalIssue) for item in self.issues):
            raise ValueError("issues contains an invalid RetrievalIssue.")
        object.__setattr__(self, "chunks", tuple(sorted(self.chunks, key=lambda item: (item.source_id, item.location, item.excerpt))))
        object.__setattr__(self, "issues", tuple(sorted(self.issues, key=lambda item: (item.source_id, item.status, item.reason))))


class RetrievalAdapter(Protocol):
    source_type: str

    def retrieve(self, request: ContextRequest, source: SourcePlanEntry) -> Iterable[EvidenceChunk]: ...


class RepositorySnapshotAdapter:
    source_type = "repository_snapshot"

    def __init__(self, snapshot: RepoSnapshot, *, retrieval_timestamp: str | None = None, confidence: float | None = None) -> None:
        if not isinstance(snapshot, RepoSnapshot):
            raise ValueError("snapshot must be a RepoSnapshot.")
        self._snapshot = snapshot
        self._retrieval_timestamp = retrieval_timestamp
        self._confidence = confidence

    def retrieve(self, request: ContextRequest, source: SourcePlanEntry) -> tuple[EvidenceChunk, ...]:
        self._validate_source(source)
        intent = request.intent.lower()
        chunks: list[EvidenceChunk] = []
        for summary in self._snapshot.summaries:
            if intent not in summary.summary.lower() and not any(seed.lower() in summary.target_path.lower() for seed in request.seed_sources):
                continue
            chunks.append(EvidenceChunk(source.source_id, summary.target_path, summary.summary, 1.0, 1.0, (source.fingerprint, self._snapshot.snapshot_id), retrieval_timestamp=self._retrieval_timestamp, confidence=self._confidence))
        return tuple(chunks)

    def _validate_source(self, source: SourcePlanEntry) -> None:
        if source.fingerprint not in {self._snapshot.content_hash, self._snapshot.snapshot_id}:
            raise ValueError("repository source fingerprint does not match the snapshot.")


class GraphTraversalAdapter:
    source_type = "graph_snapshot"

    def __init__(self, store: GraphStore, repository_id: str, start_node: str, query: GraphQuery, traversal: GraphTraversalService | None = None, *, retrieval_timestamp: str | None = None, confidence: float | None = None) -> None:
        if not isinstance(store, GraphStore):
            raise ValueError("store must be a GraphStore.")
        if not isinstance(query, GraphQuery):
            raise ValueError("query must be a GraphQuery.")
        self._store = store
        self._repository_id = repository_id
        self._start_node = start_node
        self._query = query
        self._traversal = traversal or GraphTraversalService()
        self._retrieval_timestamp = retrieval_timestamp
        self._confidence = confidence

    def retrieve(self, request: ContextRequest, source: SourcePlanEntry) -> tuple[EvidenceChunk, ...]:
        graph = self._store.load_current(self._repository_id)
        if source.fingerprint not in {graph.snapshot_id, graph.revision_id}:
            raise ValueError("graph source fingerprint does not match the published snapshot.")
        result = self._traversal.execute(graph, self._start_node, self._query)
        chunks = [EvidenceChunk(source.source_id, node.file_path, node.qualified_name, 1.0, 1.0, (graph.snapshot_id, *node.provenance), retrieval_timestamp=self._retrieval_timestamp, confidence=self._confidence) for node in result.nodes]
        chunks.extend(EvidenceChunk(source.source_id, edge.edge_id, f"{edge.kind.value}:{edge.from_node}->{edge.to_node}", edge.confidence, 1.0, (graph.snapshot_id, *edge.provenance), retrieval_timestamp=self._retrieval_timestamp, confidence=self._confidence) for edge in result.edges)
        return tuple(chunks)


class MemoryRetrievalAdapter:
    source_type = "memory"

    def __init__(self, retriever: MemoryRetriever, query: MemoryQuery, *, confidence: float | None = None, **retrieval_options: Any) -> None:
        if not isinstance(retriever, MemoryRetriever) or not isinstance(query, MemoryQuery):
            raise ValueError("retriever and query must be memory contracts.")
        self._retriever = retriever
        self._query = query
        self._options = dict(retrieval_options)
        self._confidence = confidence

    def retrieve(self, request: ContextRequest, source: SourcePlanEntry) -> tuple[EvidenceChunk, ...]:
        if source.fingerprint.strip() == "":
            raise ValueError("memory source fingerprint is invalid.")
        results = self._retriever.retrieve(self._query, **self._options)
        chunks: list[EvidenceChunk] = []
        for result in results:
            timestamp = result.item.timestamp.astimezone(UTC).isoformat()
            location = result.item.references[0] if result.item.references else result.item.memory_id
            chunks.append(EvidenceChunk(source.source_id, location, result.item.content, result.score, 1.0, (source.fingerprint, result.item.memory_id, timestamp, result.retrieval_source), retrieval_timestamp=timestamp, confidence=self._confidence))
        return tuple(chunks)


class ContextRetriever:
    """Coordinate explicit retrieval adapters without ranking or deduplication."""

    def __init__(self, adapters: Iterable[RetrievalAdapter] = ()) -> None:
        values = tuple(adapters)
        if any(not isinstance(getattr(item, "source_type", None), str) or not getattr(item, "source_type", "").strip() or not callable(getattr(item, "retrieve", None)) for item in values):
            raise ValueError("adapters must provide source_type and retrieve.")
        self._adapters = {item.source_type: item for item in values}
        if len(self._adapters) != len(values):
            raise ValueError("adapters contain duplicate source types.")

    def retrieve(self, request: ContextRequest, plan: SourcePlan) -> RetrievalResult:
        if not isinstance(request, ContextRequest):
            raise ValueError("request must be a ContextRequest.")
        if not isinstance(plan, SourcePlan):
            raise ValueError("plan must be a SourcePlan.")
        chunks: list[EvidenceChunk] = []
        issues: list[RetrievalIssue] = []
        for source in plan.entries:
            if source.status != "available":
                issues.append(RetrievalIssue(source.source_id, source.status, source.reason))
                continue
            adapter = self._adapters.get(source.source_type)
            if adapter is None:
                issues.append(RetrievalIssue(source.source_id, "unsupported", "source_type_not_supported"))
                continue
            try:
                values = tuple(adapter.retrieve(request, source))
                if any(not isinstance(item, EvidenceChunk) for item in values):
                    raise ValueError("adapter returned an invalid EvidenceChunk.")
                chunks.extend(values)
            except Exception as exc:
                issues.append(RetrievalIssue(source.source_id, "failed", type(exc).__name__))
        return RetrievalResult(tuple(chunks), tuple(issues))
