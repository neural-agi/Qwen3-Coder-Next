"""Deterministic incremental refresh for repository snapshots."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from qwen3_coder_next.repo_intelligence.classifier import FileClassifier
from qwen3_coder_next.repo_intelligence.dependencies import DependencyHintExtractor
from qwen3_coder_next.repo_intelligence.scanner import RepositoryScanner
from qwen3_coder_next.repo_intelligence.schemas import (
    ChangeEvent,
    DependencyHint,
    FileRecord,
    FolderRecord,
    RepoSnapshot,
    SummaryRecord,
)
from qwen3_coder_next.repo_intelligence.summaries import SummaryGenerator


class IncrementalRefresher:
    """Refresh a persisted snapshot while reusing unaffected records."""

    def __init__(
        self,
        scanner: RepositoryScanner | None = None,
        classifier: FileClassifier | None = None,
        dependency_extractor: DependencyHintExtractor | None = None,
        summary_generator: SummaryGenerator | None = None,
    ) -> None:
        self._scanner = scanner or RepositoryScanner()
        self._classifier = classifier or FileClassifier()
        self._dependencies = dependency_extractor or DependencyHintExtractor()
        self._summaries = summary_generator or SummaryGenerator()

    def refresh(self, snapshot: RepoSnapshot, repository_root: str | Path) -> RepoSnapshot:
        if not isinstance(snapshot, RepoSnapshot):
            raise ValueError("snapshot must be a RepoSnapshot.")
        scan = self._scanner.scan(repository_root)
        current_files = {item.normalized_path: item for item in scan.files}
        previous_files = {item.normalized_path: item for item in snapshot.files}
        changed_paths = {
            path for path, item in current_files.items()
            if path not in previous_files or self._file_changed(previous_files[path], item)
        }
        deleted_paths = set(previous_files) - set(current_files)
        affected_paths = changed_paths | deleted_paths

        files: list[FileRecord] = []
        contents: dict[str, str] = {}
        for path in sorted(current_files):
            current = current_files[path]
            if path not in changed_paths:
                files.append(previous_files[path])
                continue
            classified = self._classifier.classify(current)
            files.append(classified)
            if classified.language != "unknown":
                contents[path] = self._read_text(Path(repository_root).resolve() / Path(classified.path))
        files.sort(key=lambda item: item.normalized_path)

        previous_hints = tuple(
            hint for hint in snapshot.dependency_hints
            if hint.source_path not in affected_paths
        )
        refreshed_hints = tuple(
            hint for record in files if record.normalized_path in changed_paths
            for hint in self._dependencies.extract(record, repository_root)
        )
        hints = tuple(sorted(previous_hints + refreshed_hints, key=lambda item: (item.source_path, item.target_path, item.evidence)))

        previous_summaries = {item.target_path: item for item in snapshot.summaries}
        summaries: list[SummaryRecord] = []
        for record in files:
            if record.normalized_path not in changed_paths and record.normalized_path in previous_summaries:
                summaries.append(previous_summaries[record.normalized_path])
            else:
                summaries.append(self._summaries.summarize_file(record, content=contents.get(record.normalized_path, ""), dependency_hints=hints))

        folders = tuple(scan.folders)
        previous_folders = {item.path: item for item in snapshot.folders}
        changed_folders = {
            folder.path for folder in folders
            if folder.path not in previous_folders or folder != previous_folders[folder.path]
        }
        changed_folders.update(path for path in affected_paths for path in self._ancestors(path))
        folder_summaries = {item.target_path: item for item in snapshot.summaries if item.target_path in {folder.path for folder in snapshot.folders}}
        file_records = tuple(files)
        folder_records = tuple(folders)
        for folder in folder_records:
            if folder.path not in changed_folders and folder.path in folder_summaries:
                summaries.append(folder_summaries[folder.path])
            else:
                summaries.append(self._summaries.summarize_folder(folder, child_files=file_records, child_folders=folder_records))
        summaries.sort(key=lambda item: item.target_path)

        changes = self._changes(snapshot, previous_files, current_files, affected_paths)
        content_hash = self._content_hash(files, folders, hints, summaries)
        snapshot_id = "snapshot:" + hashlib.sha256(content_hash.encode("utf-8")).hexdigest()
        return RepoSnapshot(
            snapshot.repository_id,
            Path(repository_root).resolve().as_posix(),
            snapshot_id,
            snapshot.created_at,
            len(files),
            len(folders),
            content_hash,
            tuple(files),
            folder_records,
            hints,
            tuple(summaries),
            changes,
            snapshot.schema_version,
        )

    @staticmethod
    def _file_changed(previous: FileRecord, current: FileRecord) -> bool:
        return (previous.file_hash, previous.size_bytes) != (current.file_hash, current.size_bytes)

    @staticmethod
    def _read_text(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return ""

    @staticmethod
    def _ancestors(path: str) -> tuple[str, ...]:
        result: list[str] = []
        parent = Path(path).parent.as_posix()
        while parent != ".":
            result.append(parent)
            parent = Path(parent).parent.as_posix()
        return tuple(result)

    @staticmethod
    def _changes(snapshot: RepoSnapshot, previous: dict[str, FileRecord], current: dict[str, FileRecord], affected: set[str]) -> tuple[ChangeEvent, ...]:
        events: list[ChangeEvent] = []
        for path in sorted(affected):
            old = previous.get(path)
            new = current.get(path)
            if old is None:
                change_type = "added"
            elif new is None:
                change_type = "deleted"
            else:
                change_type = "modified"
            events.append(ChangeEvent(change_type, path, old.file_hash if old else "", new.file_hash if new else "", snapshot.created_at))
        return tuple(events)

    @staticmethod
    def _content_hash(files: Iterable[FileRecord], folders: Iterable[FolderRecord], hints: Iterable[DependencyHint], summaries: Iterable[SummaryRecord]) -> str:
        payload = {"files": [item.to_dict() for item in files], "folders": [item.to_dict() for item in folders], "dependency_hints": [item.to_dict() for item in hints], "summaries": [item.to_dict() for item in summaries]}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
