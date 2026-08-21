"""Deterministic read-only queries over repository snapshots."""
from __future__ import annotations

from dataclasses import dataclass

from qwen3_coder_next.repo_intelligence.schemas import FileRecord, FolderRecord, RepoSnapshot, SummaryRecord


def _filter_text(value: object, name: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{name} must be text.")
    return value.strip()


@dataclass(frozen=True, slots=True)
class RepositoryQueryResult:
    """Immutable result set tied to the snapshot that was queried."""

    snapshot_id: str
    files: tuple[FileRecord, ...] = ()
    folders: tuple[FolderRecord, ...] = ()
    summaries: tuple[SummaryRecord, ...] = ()


class RepositoryQueryService:
    """Answer narrow queries without rescanning or mutating a repository."""

    def query(
        self,
        snapshot: RepoSnapshot,
        *,
        path_prefix: str = "",
        file_type: str = "",
        language: str = "",
        summary_text: str = "",
    ) -> RepositoryQueryResult:
        if not isinstance(snapshot, RepoSnapshot):
            raise ValueError("snapshot must be a RepoSnapshot.")
        prefix = _filter_text(path_prefix, "path_prefix").replace("\\", "/").strip("/")
        requested_type = _filter_text(file_type, "file_type").lower()
        requested_language = _filter_text(language, "language").lower()
        requested_summary = _filter_text(summary_text, "summary_text").lower()
        files = tuple(
            sorted(
                (
                    record for record in snapshot.files
                    if self._under_prefix(record.normalized_path, prefix)
                    and (not requested_type or record.file_type.lower() == requested_type)
                    and (not requested_language or record.language.lower() == requested_language)
                ),
                key=lambda record: record.normalized_path,
            )
        )
        folders = tuple(sorted((record for record in snapshot.folders if self._under_prefix(record.path, prefix)), key=lambda record: record.path))
        summaries = tuple(
            sorted(
                (
                    record for record in snapshot.summaries
                    if self._under_prefix(record.target_path, prefix)
                    and (not requested_summary or requested_summary in record.summary.lower())
                ),
                key=lambda record: record.target_path,
            )
        )
        return RepositoryQueryResult(snapshot.snapshot_id, files, folders, summaries)

    @staticmethod
    def _under_prefix(path: str, prefix: str) -> bool:
        return not prefix or path == prefix or path.startswith(prefix + "/")
