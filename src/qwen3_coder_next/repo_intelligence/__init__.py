"""Repository intelligence contracts and canonical snapshot serialization."""

from qwen3_coder_next.repo_intelligence.schemas import (
    ChangeEvent,
    DependencyHint,
    FileRecord,
    FolderRecord,
    RepoSnapshot,
    REPOSITORY_SCHEMA_VERSION,
    SummaryRecord,
)
from qwen3_coder_next.repo_intelligence.serialization import deserialize_snapshot, serialize_snapshot
from qwen3_coder_next.repo_intelligence.scanner import DEFAULT_IGNORED_DIRECTORIES, RepositoryScanResult, RepositoryScanner
from qwen3_coder_next.repo_intelligence.classifier import FileClassifier
from qwen3_coder_next.repo_intelligence.dependencies import DependencyHintExtractor
from qwen3_coder_next.repo_intelligence.summaries import MAX_SUMMARY_LENGTH, SummaryGenerator
from qwen3_coder_next.repo_intelligence.manifest import ManifestStore
from qwen3_coder_next.repo_intelligence.refresh import IncrementalRefresher
from qwen3_coder_next.repo_intelligence.query import RepositoryQueryResult, RepositoryQueryService

__all__ = [
    "ChangeEvent",
    "DependencyHint",
    "FileRecord",
    "FolderRecord",
    "RepoSnapshot",
    "REPOSITORY_SCHEMA_VERSION",
    "SummaryRecord",
    "deserialize_snapshot",
    "serialize_snapshot",
    "DEFAULT_IGNORED_DIRECTORIES",
    "RepositoryScanResult",
    "RepositoryScanner",
    "FileClassifier",
    "DependencyHintExtractor",
    "MAX_SUMMARY_LENGTH",
    "SummaryGenerator",
    "ManifestStore",
    "IncrementalRefresher",
    "RepositoryQueryResult",
    "RepositoryQueryService",
]
