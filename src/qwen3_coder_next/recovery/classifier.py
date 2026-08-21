"""Deterministic failure diagnosis from normalized events and evidence."""
from __future__ import annotations

import re

from qwen3_coder_next.recovery.contracts import DiagnosisReport, EvidenceBundle, FailureCategory, FailureEvent

_CATEGORY_TERMS: dict[FailureCategory, frozenset[str]] = {
    FailureCategory.TRANSIENT: frozenset({"timeout", "timedout", "temporary", "unavailable", "network", "connection", "rate_limit", "flaky"}),
    FailureCategory.SEMANTIC: frozenset({"assertion", "test_failed", "validation", "mismatch", "semantic", "incorrect", "plan_failed"}),
    FailureCategory.ENVIRONMENTAL: frozenset({"permission", "denied", "missing", "not_found", "dependency", "disk", "workspace", "oom", "out_of_memory"}),
    FailureCategory.UNRECOVERABLE: frozenset({"corrupt", "corrupted", "fatal", "invalid_state", "unauthorized", "destroyed"}),
}


def _tokens(*values: str) -> set[str]:
    return {token for value in values for token in re.findall(r"[a-z0-9_]+", value.lower())}


class FailureClassifier:
    """Classify common failures using stable keyword rules only."""

    def classify(self, event: FailureEvent, evidence: EvidenceBundle) -> DiagnosisReport:
        if not isinstance(event, FailureEvent) or not isinstance(evidence, EvidenceBundle):
            raise ValueError("event and evidence are required.")
        terms = _tokens(event.failure_type, event.message, *evidence.command_output)
        matches = {category: sorted(terms.intersection(category_terms)) for category, category_terms in _CATEGORY_TERMS.items()}
        matched_categories = tuple(category for category, values in matches.items() if values)
        evidence_count = sum(len(values) for values in (evidence.recent_actions, evidence.log_refs, evidence.command_output, evidence.memory_refs, evidence.file_anchors))
        if len(matched_categories) != 1 or (not terms and evidence_count == 0):
            return DiagnosisReport(FailureCategory.UNKNOWN, "insufficient or contradictory failure evidence", 0.0, f"evidence_items={evidence_count}; matched_categories={len(matched_categories)}")
        category = matched_categories[0]
        confidence = 0.9 if len(matches[category]) > 1 else 0.75
        return DiagnosisReport(category, event.failure_type, confidence, f"evidence_items={evidence_count}; matched_terms={','.join(matches[category])}")
