"""Small deterministic in-process cache for validated context packages."""
from __future__ import annotations

from dataclasses import dataclass

from qwen3_coder_next.context_compression.budget import BudgetReport
from qwen3_coder_next.context_compression.packager import context_cache_key
from qwen3_coder_next.context_compression.schemas import ContextPackage
from qwen3_coder_next.context_compression.schemas import CompressionConfig


@dataclass(frozen=True, slots=True)
class CacheLookup:
    status: str
    package: ContextPackage | None = None


class ContextPackageCache:
    """Ephemeral cache; persistence and external backends are deliberately out of scope."""

    def __init__(self) -> None:
        self._entries: dict[str, dict[str, object]] = {}

    def put(self, key: str, package: ContextPackage, report: BudgetReport, config: CompressionConfig | None = None) -> None:
        if not isinstance(key, str) or not key.strip() or not isinstance(package, ContextPackage) or not isinstance(report, BudgetReport):
            raise ValueError("invalid cache entry.")
        if package.budget_used != report.used_budget or report.used_budget + report.reserved_budget > report.requested_budget:
            raise ValueError("cache entry is not budget-compliant.")
        if config is not None and (not isinstance(config, CompressionConfig) or report.requested_budget > config.max_tokens or package.budget_used + report.reserved_budget > config.max_tokens):
            raise ValueError("cache entry exceeds the configured maximum.")
        self._entries[key] = {"payload": package.to_dict(), "package_id": package.package_id}

    def get(self, key: str, config: CompressionConfig | None = None) -> CacheLookup:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("key must be non-empty text.")
        entry = self._entries.get(key)
        if entry is None:
            return CacheLookup("miss")
        try:
            package = ContextPackage.from_dict(entry["payload"])  # type: ignore[arg-type]
            if package.package_id != entry["package_id"]:
                return CacheLookup("invalid")
            if config is not None and (not isinstance(config, CompressionConfig) or package.budget_used > config.max_tokens):
                return CacheLookup("invalid")
        except (TypeError, ValueError, KeyError):
            return CacheLookup("invalid")
        return CacheLookup("hit", package)

    def invalidate(self, key: str) -> None:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("key must be non-empty text.")
        self._entries.pop(key, None)


__all__ = ["CacheLookup", "ContextPackageCache", "context_cache_key"]
