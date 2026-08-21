"""Canonical JSON serialization for graph foundation contracts."""
from __future__ import annotations

import json

from qwen3_coder_next.graph.schemas import GraphSnapshot


def serialize_graph_snapshot(snapshot: GraphSnapshot) -> str:
    if not isinstance(snapshot, GraphSnapshot):
        raise ValueError("snapshot must be a GraphSnapshot.")
    return json.dumps(snapshot.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def deserialize_graph_snapshot(payload: str | bytes) -> GraphSnapshot:
    if not isinstance(payload, (str, bytes)):
        raise ValueError("graph snapshot payload must be text or bytes.")
    try:
        value = json.loads(payload)
    except (TypeError, ValueError) as exc:
        raise ValueError("graph snapshot payload is not valid JSON.") from exc
    return GraphSnapshot.from_dict(value)
