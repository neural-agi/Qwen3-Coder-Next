"""Deterministic provenance packaging for Part 11 Step 7."""
from __future__ import annotations

import hashlib
import json

from qwen3_coder_next.context_compression.budget import BudgetResult, estimate_tokens
from qwen3_coder_next.context_compression.schemas import (
    CompressionConfig,
    ContextPackage,
    ContextRequest,
    EvidenceChunk,
    canonical_package_id,
    compression_config_fingerprint,
    context_request_fingerprint,
)
from qwen3_coder_next.context_compression.source_resolver import SourcePlan
from qwen3_coder_next.context_compression.summarizer import SummaryResult


class ContextPackager:
    """Assemble only validated upstream outputs; never retrieve or trim evidence."""

    def package(
        self,
        request: ContextRequest,
        summary: SummaryResult,
        budget: BudgetResult,
        evidence: object,
        source_plan: SourcePlan,
        config: CompressionConfig,
    ) -> ContextPackage:
        if not isinstance(request, ContextRequest) or not isinstance(summary, SummaryResult):
            raise ValueError("request and summary must use context contracts.")
        if not isinstance(budget, BudgetResult) or not budget.feasible:
            raise ValueError("budget result is infeasible.")
        if not isinstance(source_plan, SourcePlan) or not isinstance(config, CompressionConfig):
            raise ValueError("source_plan and config must use context contracts.")
        chunks = self._validate_evidence(evidence)
        accepted = tuple(budget.accepted_claims)
        selected: list[EvidenceChunk] = []
        for claim in accepted:
            matches = [chunk for chunk in chunks if chunk.source_id == claim.source_id and chunk.location == claim.location and claim.text in chunk.excerpt and chunk.retrieval_timestamp == claim.retrieval_timestamp and chunk.confidence == claim.confidence]
            if len(matches) != 1:
                raise ValueError("accepted claim lacks unique source provenance.")
            selected.append(matches[0])
        if estimate_tokens(budget.rendered_summary) != budget.report.used_budget:
            raise ValueError("budget result does not match its rendered representation.")
        if budget.report.requested_budget > config.max_tokens or budget.report.used_budget + budget.report.reserved_budget > config.max_tokens:
            raise ValueError("budget result exceeds the configured maximum.")
        if budget.report.used_budget + budget.report.reserved_budget > budget.report.requested_budget:
            raise ValueError("budget result exceeds its hard ceiling.")
        provenance = tuple((chunk.source_id, (chunk.location,)) for chunk in sorted(selected, key=lambda item: (item.source_id, item.location, item.excerpt)))
        source_fingerprints = tuple(entry.fingerprint for entry in source_plan.entries)
        evidence_identity = hashlib.sha256(json.dumps([chunk.to_dict() for chunk in selected], sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
        policy = f"{summary.policy_version}:{compression_config_fingerprint(config)}:reserved={budget.report.reserved_budget}:evidence={evidence_identity}"
        package_id = canonical_package_id(request.task_id, context_request_fingerprint(request), source_fingerprints, policy)
        omissions = tuple(sorted(set((*summary.omissions, *budget.omissions))))
        coverage = tuple(sorted({f"included:{chunk.source_id}:{chunk.location}" for chunk in selected} | {f"omitted:{item}" for item in omissions}))
        return ContextPackage(package_id, request.task_id, tuple(selected), budget.rendered_summary, budget.report.used_budget, omissions, dict(provenance), coverage_notes=coverage)

    @staticmethod
    def _validate_evidence(evidence: object) -> tuple[EvidenceChunk, ...]:
        if isinstance(evidence, (str, bytes)):
            raise ValueError("evidence must be a collection of EvidenceChunk values.")
        try:
            values = tuple(evidence or ())  # type: ignore[arg-type]
        except TypeError as exc:
            raise ValueError("evidence must be a collection of EvidenceChunk values.") from exc
        if any(not isinstance(chunk, EvidenceChunk) for chunk in values):
            raise ValueError("evidence contains an invalid EvidenceChunk.")
        return values


def context_cache_key(request: ContextRequest, source_plan: SourcePlan, config: CompressionConfig, policy_version: str, reserved_budget: int, evidence: object = ()) -> str:
    if not isinstance(request, ContextRequest) or not isinstance(source_plan, SourcePlan) or not isinstance(config, CompressionConfig):
        raise ValueError("invalid cache-key inputs.")
    if not isinstance(policy_version, str) or not policy_version.strip():
        raise ValueError("policy_version must be non-empty text.")
    if not isinstance(reserved_budget, int) or isinstance(reserved_budget, bool) or reserved_budget < 0:
        raise ValueError("reserved_budget must be a non-negative integer.")
    if isinstance(evidence, (str, bytes)):
        raise ValueError("evidence must be a collection of EvidenceChunk values.")
    try:
        evidence_values = tuple(evidence or ())
    except TypeError as exc:
        raise ValueError("evidence must be a collection of EvidenceChunk values.") from exc
    if any(not isinstance(chunk, EvidenceChunk) for chunk in evidence_values):
        raise ValueError("evidence contains an invalid EvidenceChunk.")
    payload = {
        "request": context_request_fingerprint(request),
        "sources": [entry.__dict__ if hasattr(entry, "__dict__") else {"source_id": entry.source_id, "source_type": entry.source_type, "fingerprint": entry.fingerprint, "priority": entry.priority, "status": entry.status, "reason": entry.reason} for entry in source_plan.entries],
        "config": compression_config_fingerprint(config),
        "policy_version": policy_version.strip(),
        "reserved_budget": reserved_budget,
        "evidence": [chunk.to_dict() for chunk in sorted(evidence_values, key=lambda item: (item.source_id, item.location, item.excerpt, item.provenance))],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return "context-cache:" + hashlib.sha256(encoded).hexdigest()
