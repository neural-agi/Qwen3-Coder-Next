"""Versioned immutable contracts for the repository intelligence foundation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

REPOSITORY_SCHEMA_VERSION = 1


def _text(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f"{name} must be non-empty text.")
    return value.strip() if not allow_empty else value


def _texts(value: object, name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must be a collection of text.")
    try:
        values = tuple(value or ())  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValueError(f"{name} must be a collection of text.") from exc
    if any(not isinstance(item, str) or not item.strip() for item in values):
        raise ValueError(f"{name} contains invalid text.")
    return tuple(item.strip() for item in values)


def _records(value: object, name: str, expected: type) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must be a collection of records.")
    try:
        values = tuple(value or ())  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValueError(f"{name} must be a collection of records.") from exc
    if any(not isinstance(item, expected) for item in values):
        raise ValueError(f"{name} contains an invalid record.")
    return values


@dataclass(frozen=True, slots=True)
class FileRecord:
    """One deterministically identified file in a repository snapshot."""

    path: str
    normalized_path: str
    file_type: str
    language: str
    size_bytes: int
    file_hash: str
    summary_ref: str = ""
    dependency_refs: tuple[str, ...] = ()
    schema_version: int = REPOSITORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("path", "normalized_path", "file_type", "language", "file_hash"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if not isinstance(self.size_bytes, int) or self.size_bytes < 0:
            raise ValueError("size_bytes must be a non-negative integer.")
        object.__setattr__(self, "summary_ref", _text(self.summary_ref, "summary_ref", allow_empty=True))
        object.__setattr__(self, "dependency_refs", _texts(self.dependency_refs, "dependency_refs"))

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "normalized_path": self.normalized_path, "file_type": self.file_type, "language": self.language, "size_bytes": self.size_bytes, "hash": self.file_hash, "summary_ref": self.summary_ref, "dependency_refs": list(self.dependency_refs), "schema_version": self.schema_version}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FileRecord":
        if not isinstance(payload, dict):
            raise ValueError("file record payload must be a mapping.")
        return cls(payload["path"], payload["normalized_path"], payload["file_type"], payload["language"], int(payload["size_bytes"]), payload.get("hash", payload.get("file_hash", "")), payload.get("summary_ref", ""), tuple(payload.get("dependency_refs", ())), int(payload.get("schema_version", REPOSITORY_SCHEMA_VERSION)))


@dataclass(frozen=True, slots=True)
class FolderRecord:
    """One repository folder navigation record."""

    path: str
    child_file_count: int
    child_folder_count: int
    dominant_languages: tuple[str, ...] = ()
    summary_ref: str = ""
    schema_version: int = REPOSITORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _text(self.path, "path"))
        for name in ("child_file_count", "child_folder_count"):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")
        object.__setattr__(self, "dominant_languages", _texts(self.dominant_languages, "dominant_languages"))
        object.__setattr__(self, "summary_ref", _text(self.summary_ref, "summary_ref", allow_empty=True))

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "child_file_count": self.child_file_count, "child_folder_count": self.child_folder_count, "dominant_languages": list(self.dominant_languages), "summary_ref": self.summary_ref, "schema_version": self.schema_version}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FolderRecord":
        if not isinstance(payload, dict):
            raise ValueError("folder record payload must be a mapping.")
        return cls(payload["path"], int(payload["child_file_count"]), int(payload["child_folder_count"]), tuple(payload.get("dominant_languages", ())), payload.get("summary_ref", ""), int(payload.get("schema_version", REPOSITORY_SCHEMA_VERSION)))


@dataclass(frozen=True, slots=True)
class DependencyHint:
    """A shallow dependency signal with explicit evidence and confidence."""

    source_path: str
    target_path: str
    hint_type: str
    confidence: float
    evidence: str
    schema_version: int = REPOSITORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("source_path", "target_path", "hint_type", "evidence"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if not isinstance(self.confidence, (int, float)) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1.")

    def to_dict(self) -> dict[str, Any]:
        return {"source_path": self.source_path, "target_path": self.target_path, "hint_type": self.hint_type, "confidence": self.confidence, "evidence": self.evidence, "schema_version": self.schema_version}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DependencyHint":
        if not isinstance(payload, dict):
            raise ValueError("dependency hint payload must be a mapping.")
        return cls(payload["source_path"], payload["target_path"], payload["hint_type"], float(payload["confidence"]), payload["evidence"], int(payload.get("schema_version", REPOSITORY_SCHEMA_VERSION)))


@dataclass(frozen=True, slots=True)
class SummaryRecord:
    """A concise summary reference for a file or folder."""

    summary_id: str
    target_path: str
    summary: str
    created_at: str
    schema_version: int = REPOSITORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("summary_id", "target_path", "summary", "created_at"):
            object.__setattr__(self, name, _text(getattr(self, name), name))

    def to_dict(self) -> dict[str, Any]:
        return {"summary_id": self.summary_id, "target_path": self.target_path, "summary": self.summary, "created_at": self.created_at, "schema_version": self.schema_version}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SummaryRecord":
        if not isinstance(payload, dict):
            raise ValueError("summary payload must be a mapping.")
        return cls(payload["summary_id"], payload["target_path"], payload["summary"], payload["created_at"], int(payload.get("schema_version", REPOSITORY_SCHEMA_VERSION)))


@dataclass(frozen=True, slots=True)
class ChangeEvent:
    """A deterministic record of one path hash change."""

    change_type: str
    path: str
    previous_hash: str
    current_hash: str
    timestamp: str
    schema_version: int = REPOSITORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("change_type", "path", "previous_hash", "current_hash", "timestamp"):
            object.__setattr__(self, name, _text(getattr(self, name), name, allow_empty=name in {"previous_hash", "current_hash"}))

    def to_dict(self) -> dict[str, Any]:
        return {"change_type": self.change_type, "path": self.path, "previous_hash": self.previous_hash, "current_hash": self.current_hash, "timestamp": self.timestamp, "schema_version": self.schema_version}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ChangeEvent":
        if not isinstance(payload, dict):
            raise ValueError("change event payload must be a mapping.")
        return cls(payload["change_type"], payload["path"], payload.get("previous_hash", ""), payload.get("current_hash", ""), payload["timestamp"], int(payload.get("schema_version", REPOSITORY_SCHEMA_VERSION)))


@dataclass(frozen=True, slots=True)
class RepoSnapshot:
    """Immutable repository view consumed by later intelligence components."""

    repository_id: str
    root_path: str
    snapshot_id: str
    created_at: str
    file_count: int
    folder_count: int
    content_hash: str
    files: tuple[FileRecord, ...] = field(default_factory=tuple)
    folders: tuple[FolderRecord, ...] = field(default_factory=tuple)
    dependency_hints: tuple[DependencyHint, ...] = field(default_factory=tuple)
    summaries: tuple[SummaryRecord, ...] = field(default_factory=tuple)
    changes: tuple[ChangeEvent, ...] = field(default_factory=tuple)
    schema_version: int = REPOSITORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("repository_id", "root_path", "snapshot_id", "created_at", "content_hash"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in ("file_count", "folder_count"):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")
        object.__setattr__(self, "files", _records(self.files, "files", FileRecord))
        object.__setattr__(self, "folders", _records(self.folders, "folders", FolderRecord))
        object.__setattr__(self, "dependency_hints", _records(self.dependency_hints, "dependency_hints", DependencyHint))
        object.__setattr__(self, "summaries", _records(self.summaries, "summaries", SummaryRecord))
        object.__setattr__(self, "changes", _records(self.changes, "changes", ChangeEvent))

    def to_dict(self) -> dict[str, Any]:
        return {"repository_id": self.repository_id, "root_path": self.root_path, "snapshot_id": self.snapshot_id, "created_at": self.created_at, "file_count": self.file_count, "folder_count": self.folder_count, "content_hash": self.content_hash, "files": [item.to_dict() for item in self.files], "folders": [item.to_dict() for item in self.folders], "dependency_hints": [item.to_dict() for item in self.dependency_hints], "summaries": [item.to_dict() for item in self.summaries], "changes": [item.to_dict() for item in self.changes], "schema_version": self.schema_version}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RepoSnapshot":
        if not isinstance(payload, dict):
            raise ValueError("repository snapshot payload must be a mapping.")
        required = ("repository_id", "root_path", "snapshot_id", "created_at", "file_count", "folder_count", "content_hash")
        if any(name not in payload for name in required):
            raise ValueError("repository snapshot payload is missing required fields.")
        return cls(payload["repository_id"], payload["root_path"], payload["snapshot_id"], payload["created_at"], int(payload["file_count"]), int(payload["folder_count"]), payload["content_hash"], tuple(FileRecord.from_dict(item) for item in payload.get("files", ())), tuple(FolderRecord.from_dict(item) for item in payload.get("folders", ())), tuple(DependencyHint.from_dict(item) for item in payload.get("dependency_hints", ())), tuple(SummaryRecord.from_dict(item) for item in payload.get("summaries", ())), tuple(ChangeEvent.from_dict(item) for item in payload.get("changes", ())), int(payload.get("schema_version", REPOSITORY_SCHEMA_VERSION)))
