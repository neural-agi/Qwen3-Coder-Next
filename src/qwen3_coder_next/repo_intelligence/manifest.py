"""Deterministic local persistence for repository intelligence snapshots."""
from __future__ import annotations

import json
import os
from pathlib import Path

from qwen3_coder_next.repo_intelligence.schemas import REPOSITORY_SCHEMA_VERSION, RepoSnapshot
from qwen3_coder_next.repo_intelligence.serialization import deserialize_snapshot, serialize_snapshot


class ManifestStore:
    """Persist and reload one repository snapshot without indexing or query behavior."""

    def save(self, snapshot: RepoSnapshot, manifest_path: str | Path) -> Path:
        if not isinstance(snapshot, RepoSnapshot):
            raise ValueError("snapshot must be a RepoSnapshot.")
        path = self._path(manifest_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        try:
            temporary.write_text(serialize_snapshot(snapshot), encoding="utf-8", newline="\n")
            os.replace(temporary, path)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise ValueError("manifest could not be saved.") from exc
        return path

    def load(self, manifest_path: str | Path) -> RepoSnapshot:
        path = self._path(manifest_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(str(path))
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("manifest is missing, unreadable, or corrupted.") from exc
        if not isinstance(payload, dict):
            raise ValueError("manifest payload must be a mapping.")
        if payload.get("schema_version", REPOSITORY_SCHEMA_VERSION) != REPOSITORY_SCHEMA_VERSION:
            raise ValueError("manifest schema version is incompatible.")
        try:
            return deserialize_snapshot(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError("manifest does not match the repository snapshot schema.") from exc

    @staticmethod
    def _path(value: str | Path) -> Path:
        if not isinstance(value, (str, Path)) or not str(value).strip():
            raise ValueError("manifest_path must be a non-empty path.")
        return Path(value)
