"""Part 11 Context Compression contracts."""

from qwen3_coder_next.context_compression.schemas import (
    CONTEXT_COMPRESSION_SCHEMA_VERSION,
    BudgetReport,
    CompressionConfig,
    ContextPackage,
    ContextRequest,
    EvidenceChunk,
    canonical_package_id,
    compression_config_fingerprint,
    context_request_fingerprint,
)
from qwen3_coder_next.context_compression.request_normalizer import ContextRequestNormalizer
from qwen3_coder_next.context_compression.source_resolver import SourcePlan, SourcePlanEntry, SourceResolver, SourceSpec
from qwen3_coder_next.context_compression.retriever import (
    ContextRetriever,
    GraphTraversalAdapter,
    MemoryRetrievalAdapter,
    RepositorySnapshotAdapter,
    RetrievalIssue,
    RetrievalResult,
)
from qwen3_coder_next.context_compression.ranker import DeduplicationResult, EvidenceDeduplicator, EvidenceRanker, RankingResult
from qwen3_coder_next.context_compression.summarizer import EvidenceSummarizer, SummaryClaim, SummaryPolicy, SummaryPolicyRegistry, SummaryResult
from qwen3_coder_next.context_compression.budget import BudgetManager, BudgetResult, estimate_tokens
from qwen3_coder_next.context_compression.packager import ContextPackager, context_cache_key
from qwen3_coder_next.context_compression.cache import CacheLookup, ContextPackageCache
from qwen3_coder_next.context_compression.telemetry import CompressionTelemetry, CompressionTelemetryEvent
from qwen3_coder_next.context_compression.fallback import ContextFallback, FallbackResult
from qwen3_coder_next.context_compression.pipeline import ContextCompressionPipeline, ContextPipelineResult
from qwen3_coder_next.context_compression.rehydration import ContextRehydrator

__all__ = [
    "CONTEXT_COMPRESSION_SCHEMA_VERSION",
    "BudgetReport",
    "CompressionConfig",
    "ContextPackage",
    "ContextRequest",
    "EvidenceChunk",
    "canonical_package_id",
    "compression_config_fingerprint",
    "context_request_fingerprint",
    "ContextRequestNormalizer",
    "SourcePlan",
    "SourcePlanEntry",
    "SourceResolver",
    "SourceSpec",
    "ContextRetriever",
    "GraphTraversalAdapter",
    "MemoryRetrievalAdapter",
    "RepositorySnapshotAdapter",
    "RetrievalIssue",
    "RetrievalResult",
    "DeduplicationResult",
    "EvidenceDeduplicator",
    "EvidenceRanker",
    "RankingResult",
    "EvidenceSummarizer",
    "SummaryClaim",
    "SummaryPolicy",
    "SummaryPolicyRegistry",
    "SummaryResult",
    "BudgetManager",
    "BudgetResult",
    "estimate_tokens",
    "ContextPackager",
    "context_cache_key",
    "CacheLookup",
    "ContextPackageCache",
    "CompressionTelemetry",
    "CompressionTelemetryEvent",
    "ContextFallback",
    "FallbackResult",
    "ContextCompressionPipeline",
    "ContextPipelineResult",
    "ContextRehydrator",
]
