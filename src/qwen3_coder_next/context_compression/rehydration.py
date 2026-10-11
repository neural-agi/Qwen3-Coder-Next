"""Provenance-only evidence rehydration for supported source adapters."""
from __future__ import annotations

from collections.abc import Callable, Mapping

from qwen3_coder_next.context_compression.schemas import ContextPackage, EvidenceChunk
from qwen3_coder_next.context_compression.source_resolver import SourcePlan


class ContextRehydrator:
    def rehydrate(self, package: ContextPackage, source_plan: SourcePlan, adapters: Mapping[str, Callable[[str], EvidenceChunk]]) -> tuple[EvidenceChunk, ...]:
        if not isinstance(package, ContextPackage) or not isinstance(source_plan, SourcePlan) or not isinstance(adapters, Mapping):
            raise ValueError("invalid rehydration inputs.")
        fingerprints = {entry.source_id: entry.fingerprint for entry in source_plan.entries}
        restored: list[EvidenceChunk] = []
        for source_id, locations in package.provenance_map:
            adapter = adapters.get(source_id)
            if adapter is None or source_id not in fingerprints:
                raise ValueError("source adapter or fingerprint is missing.")
            for location in locations:
                chunk = adapter(location)
                if not isinstance(chunk, EvidenceChunk) or chunk.source_id != source_id or chunk.location != location or fingerprints[source_id] not in chunk.provenance:
                    raise ValueError("rehydrated evidence does not match provenance.")
                restored.append(chunk)
        return tuple(sorted(restored, key=lambda item: (item.source_id, item.location, item.excerpt)))
