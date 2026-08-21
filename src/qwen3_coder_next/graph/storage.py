"""Deterministic local persistence and publication for graph snapshots."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from qwen3_coder_next.graph.schemas import GraphSnapshot
from qwen3_coder_next.graph.serialization import deserialize_graph_snapshot, serialize_graph_snapshot


class GraphStore:
    """Persist immutable graph snapshots and publish one current snapshot per repository."""

    def __init__(self, storage_root: str | Path) -> None:
        if not isinstance(storage_root, (str, Path)) or not str(storage_root).strip():
            raise ValueError("storage_root must be a non-empty path.")
        self._root = Path(storage_root)

    def save(self, snapshot: GraphSnapshot) -> Path:
        if not isinstance(snapshot, GraphSnapshot):
            raise ValueError("snapshot must be a GraphSnapshot.")
        path = self._snapshot_path(snapshot.repo_id, snapshot.snapshot_id)
        self._atomic_write(path, serialize_graph_snapshot(snapshot))
        return path

    def load(self, repo_id: str, snapshot_id: str) -> GraphSnapshot:
        path = self._snapshot_path(repo_id, snapshot_id)
        if not path.is_file():
            raise FileNotFoundError(str(path))
        snapshot = self._read(path)
        if snapshot.repo_id != repo_id or snapshot.snapshot_id != snapshot_id:
            raise ValueError("stored graph snapshot identity does not match the requested identity.")
        return snapshot

    def publish(self, snapshot: GraphSnapshot) -> Path:
        path = self.save(snapshot)
        pointer = self._current_path(snapshot.repo_id)
        payload = json.dumps({"repo_id": snapshot.repo_id, "snapshot_id": snapshot.snapshot_id, "revision_id": snapshot.revision_id}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        self._atomic_write(pointer, payload)
        return path

    def load_current(self, repo_id: str) -> GraphSnapshot:
        pointer = self._current_path(repo_id)
        if not pointer.is_file():
            raise FileNotFoundError(str(pointer))
        try:
            payload = json.loads(pointer.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("repo_id") != repo_id or not isinstance(payload.get("snapshot_id"), str):
                raise ValueError
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError("current graph publication is missing or corrupted.") from exc
        return self.load(repo_id, payload["snapshot_id"])

    def _snapshot_path(self, repo_id: str, snapshot_id: str) -> Path:
        key = self._identity_key(repo_id, snapshot_id)
        return self._root / "snapshots" / f"{key}.json"

    def _current_path(self, repo_id: str) -> Path:
        return self._root / "current" / f"{self._safe_key(repo_id)}.json"

    @staticmethod
    def _safe_key(value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("graph identity must be non-empty text.")
        return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()

    @classmethod
    def _identity_key(cls, repo_id: str, snapshot_id: str) -> str:
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            raise ValueError("snapshot_id must be non-empty text.")
        return cls._safe_key(f"{repo_id.strip()}\0{snapshot_id.strip()}")

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        try:
            temporary.write_text(content, encoding="utf-8", newline="\n")
            os.replace(temporary, path)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise ValueError("graph snapshot could not be persisted.") from exc

    @staticmethod
    def _read(path: Path) -> GraphSnapshot:
        try:
            return deserialize_graph_snapshot(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
            raise ValueError("graph snapshot is missing, unreadable, or corrupted.") from exc
