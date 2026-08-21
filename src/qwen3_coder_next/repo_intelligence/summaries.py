"""Deterministic shallow file and folder summary generation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from qwen3_coder_next.repo_intelligence.schemas import DependencyHint, FileRecord, FolderRecord, SummaryRecord

MAX_SUMMARY_LENGTH = 240


class SummaryGenerator:
    """Create bounded summaries from repository metadata and lightweight snippets."""

    def __init__(self, max_length: int = MAX_SUMMARY_LENGTH) -> None:
        if not isinstance(max_length, int) or max_length <= 0:
            raise ValueError("max_length must be a positive integer.")
        self._max_length = max_length

    def _summary_id(self, target_path: str, payload: object) -> str:
        canonical = json.dumps({"target_path": target_path, "payload": payload}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return "summary:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _bounded(self, text: str) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= self._max_length:
            return normalized
        return normalized[: self._max_length - 3].rstrip() + "..."

    def summarize_file(
        self,
        record: FileRecord,
        *,
        content: str = "",
        dependency_hints: Iterable[DependencyHint] = (),
    ) -> SummaryRecord:
        if not isinstance(record, FileRecord) or not isinstance(content, str):
            raise ValueError("record must be a FileRecord and content must be text.")
        if isinstance(dependency_hints, (str, bytes)):
            raise ValueError("dependency_hints must be a collection of DependencyHint values.")
        try:
            hints = tuple(dependency_hints)
        except TypeError as exc:
            raise ValueError("dependency_hints must be a collection of DependencyHint values.") from exc
        if any(not isinstance(hint, DependencyHint) for hint in hints):
            raise ValueError("dependency_hints contains an invalid value.")
        relevant = tuple(sorted((hint for hint in hints if hint.source_path == record.normalized_path), key=lambda hint: (hint.target_path, hint.evidence)))
        declaration = next((line.strip() for line in content.splitlines() if line.strip() and not line.lstrip().startswith(("#", "//", "/*", "*"))), "")
        hint_text = ""
        if relevant:
            targets = ", ".join(hint.target_path for hint in relevant[:4])
            hint_text = f" Dependencies: {targets}."
        body = f"{record.file_type} file {record.normalized_path} ({record.language})."
        if declaration:
            body += f" First declaration: {declaration}."
        body += hint_text
        summary = self._bounded(body)
        summary_id = self._summary_id(record.normalized_path, {"hash": record.file_hash, "summary": summary, "hints": [hint.to_dict() for hint in relevant]})
        return SummaryRecord(summary_id, record.normalized_path, summary, "derived")

    def summarize_folder(self, record: FolderRecord, *, child_files: Iterable[FileRecord] = (), child_folders: Iterable[FolderRecord] = ()) -> SummaryRecord:
        if not isinstance(record, FolderRecord):
            raise ValueError("record must be a FolderRecord.")
        for values, expected, name in ((child_files, FileRecord, "child_files"), (child_folders, FolderRecord, "child_folders")):
            if isinstance(values, (str, bytes)):
                raise ValueError(f"{name} must be a collection of records.")
            try:
                values_tuple = tuple(values)
            except TypeError as exc:
                raise ValueError(f"{name} must be a collection of records.") from exc
            if any(not isinstance(value, expected) for value in values_tuple):
                raise ValueError(f"{name} contains an invalid record.")
            if name == "child_files":
                files = values_tuple
            else:
                folders = values_tuple
        languages = tuple(sorted({file.language for file in files if file.language != "unknown"}))
        names = tuple(sorted(file.normalized_path for file in files)[:3])
        language_text = ", ".join(languages) if languages else "unknown languages"
        name_text = ", ".join(names) if names else "no files"
        summary = self._bounded(f"Folder {record.path} contains {record.child_file_count} files and {record.child_folder_count} child folders; languages: {language_text}; files: {name_text}.")
        summary_id = self._summary_id(record.path, {"summary": summary, "files": names, "folders": sorted(folder.path for folder in folders)})
        return SummaryRecord(summary_id, record.path, summary, "derived")

    def summarize_files(self, records: Iterable[FileRecord], *, contents: dict[str, str] | None = None, dependency_hints: Iterable[DependencyHint] = ()) -> tuple[SummaryRecord, ...]:
        if isinstance(records, (str, bytes)):
            raise ValueError("records must be a collection of FileRecord values.")
        contents = {} if contents is None else contents
        if not isinstance(contents, dict) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in contents.items()):
            raise ValueError("contents must be a text mapping.")
        values = tuple(records)
        return tuple(self.summarize_file(record, content=contents.get(record.normalized_path, ""), dependency_hints=dependency_hints) for record in sorted(values, key=lambda item: item.normalized_path))

    def summarize_folders(self, records: Iterable[FolderRecord], *, files: Iterable[FileRecord] = (), folders: Iterable[FolderRecord] = ()) -> tuple[SummaryRecord, ...]:
        if isinstance(records, (str, bytes)):
            raise ValueError("records must be a collection of FolderRecord values.")
        file_values = tuple(files)
        folder_values = tuple(folders)
        return tuple(self.summarize_folder(record, child_files=file_values, child_folders=folder_values) for record in sorted(tuple(records), key=lambda item: item.path))
