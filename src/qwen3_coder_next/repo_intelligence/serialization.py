"""Canonical serialization helpers for repository intelligence contracts."""
from __future__ import annotations

import json
from typing import Any

from qwen3_coder_next.repo_intelligence.schemas import RepoSnapshot


def serialize_snapshot(snapshot: RepoSnapshot) -> str:
    """Return deterministic JSON for a repository snapshot."""
    if not isinstance(snapshot, RepoSnapshot):
        raise ValueError("snapshot must be a RepoSnapshot.")
    return json.dumps(snapshot.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def deserialize_snapshot(payload: str | bytes) -> RepoSnapshot:
    """Deserialize one canonical or compatible snapshot payload."""
    if not isinstance(payload, (str, bytes)):
        raise ValueError("snapshot payload must be text or bytes.")
    try:
        value: Any = json.loads(payload)
    except (TypeError, ValueError) as exc:
        raise ValueError("snapshot payload is not valid JSON.") from exc
    if not isinstance(value, dict):
        raise ValueError("snapshot payload must contain a mapping.")
    return RepoSnapshot.from_dict(value)
