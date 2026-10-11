"""Deterministic normalization into the Part 11 ContextRequest contract."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from qwen3_coder_next.context_compression.schemas import ContextRequest
from qwen3_coder_next.contracts import TaskRequest


class ContextRequestNormalizer:
    """Convert supported task-shaped inputs without changing their intent."""

    def normalize(self, raw: ContextRequest | TaskRequest | Mapping[str, Any]) -> ContextRequest:
        if isinstance(raw, ContextRequest):
            return raw
        if isinstance(raw, TaskRequest):
            metadata = raw.metadata if isinstance(raw.metadata, dict) else {}
            role = metadata.get("agent_role", "unknown")
            return ContextRequest(
                raw.task_id,
                role,
                raw.objective,
                metadata.get("token_budget", 1),
                metadata.get("seed_sources", ()),
                metadata.get("freshness_window", 0),
            )
        if not isinstance(raw, Mapping):
            raise ValueError("context request input must be a ContextRequest, TaskRequest, or mapping.")
        required = ("task_id", "agent_role", "intent", "token_budget", "seed_sources", "freshness_window")
        missing = tuple(name for name in required if name not in raw)
        if missing:
            raise ValueError(f"context request is missing required fields: {', '.join(missing)}")
        return ContextRequest(
            raw["task_id"],
            raw["agent_role"],
            raw["intent"],
            raw["token_budget"],
            raw["seed_sources"],
            raw["freshness_window"],
        )
