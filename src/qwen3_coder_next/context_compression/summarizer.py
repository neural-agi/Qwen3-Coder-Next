"""Deterministic extractive summarization for Part 11 Step 5."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from qwen3_coder_next.context_compression.schemas import CompressionConfig, ContextRequest, EvidenceChunk


_ACTIONABLE = re.compile(r"(?:^|\s)(?:[$>#]|(?:python|uv|git|npm|pytest)\b)|(?:/|\\)[\w./\\-]+|\b(?:error|exception|failed|id|identifier)\b", re.IGNORECASE)
_DEFAULT_POLICY_VERSION = "extractive-default-v1"
_DEFAULT_SUMMARY_BUDGET = 1000


@dataclass(frozen=True, slots=True)
class SummaryPolicy:
    """Small, explicit role policy; it does not perform semantic inference."""

    role: str
    policy_version: str = _DEFAULT_POLICY_VERSION
    highlight_limit: int = 5
    preserve_actionable: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.role, str) or not self.role.strip():
            raise ValueError("role must be non-empty text.")
        if not isinstance(self.policy_version, str) or not self.policy_version.strip():
            raise ValueError("policy_version must be non-empty text.")
        if not isinstance(self.highlight_limit, int) or isinstance(self.highlight_limit, bool) or self.highlight_limit <= 0:
            raise ValueError("highlight_limit must be a positive integer.")
        if not isinstance(self.preserve_actionable, bool):
            raise ValueError("preserve_actionable must be boolean.")
        object.__setattr__(self, "role", self.role.strip())
        object.__setattr__(self, "policy_version", self.policy_version.strip())


@dataclass(frozen=True, slots=True)
class SummaryClaim:
    text: str
    source_id: str
    location: str
    retrieval_timestamp: str
    confidence: float

    def __post_init__(self) -> None:
        for name in ("text", "source_id", "location", "retrieval_timestamp"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text.")
            object.__setattr__(self, name, value.strip())
        if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1.")
        object.__setattr__(self, "confidence", float(self.confidence))


@dataclass(frozen=True, slots=True)
class SummaryResult:
    summary: str = ""
    highlights: tuple[str, ...] = field(default_factory=tuple)
    omissions: tuple[str, ...] = field(default_factory=tuple)
    claims: tuple[SummaryClaim, ...] = field(default_factory=tuple)
    policy_version: str = _DEFAULT_POLICY_VERSION
    budget_exceeded: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.summary, str):
            raise ValueError("summary must be text.")
        if any(not isinstance(value, str) or not value.strip() for value in (*self.highlights, *self.omissions)):
            raise ValueError("highlights and omissions must contain non-empty text.")
        if any(not isinstance(value, SummaryClaim) for value in self.claims):
            raise ValueError("claims contains an invalid SummaryClaim.")
        if not isinstance(self.policy_version, str) or not self.policy_version.strip():
            raise ValueError("policy_version must be non-empty text.")
        if not isinstance(self.budget_exceeded, bool):
            raise ValueError("budget_exceeded must be boolean.")
        object.__setattr__(self, "summary", self.summary)
        object.__setattr__(self, "highlights", tuple(self.highlights))
        object.__setattr__(self, "omissions", tuple(self.omissions))
        object.__setattr__(self, "claims", tuple(self.claims))


class SummaryPolicyRegistry:
    def __init__(self, policies: Iterable[SummaryPolicy] = ()) -> None:
        values = tuple(policies)
        if any(not isinstance(policy, SummaryPolicy) for policy in values):
            raise ValueError("policies must contain SummaryPolicy values.")
        self._policies = {policy.role: policy for policy in values}
        if len(self._policies) != len(values):
            raise ValueError("policies contain duplicate roles.")

    def resolve(self, role: str) -> SummaryPolicy:
        if not isinstance(role, str) or not role.strip():
            raise ValueError("role must be non-empty text.")
        return self._policies.get(role.strip(), SummaryPolicy(role.strip()))


class EvidenceSummarizer:
    """Create bounded, source-linked extractive summaries without semantic claims."""

    def __init__(self, policies: SummaryPolicyRegistry | None = None) -> None:
        self._policies = policies or SummaryPolicyRegistry()

    def summarize(
        self,
        request: ContextRequest,
        chunks: object,
        config: CompressionConfig,
        summary_budget: int = _DEFAULT_SUMMARY_BUDGET,
    ) -> SummaryResult:
        if not isinstance(request, ContextRequest):
            raise ValueError("request must be a ContextRequest.")
        if not isinstance(config, CompressionConfig):
            raise ValueError("config must be a CompressionConfig.")
        if not isinstance(summary_budget, int) or isinstance(summary_budget, bool) or summary_budget <= 0:
            raise ValueError("summary_budget must be a positive integer.")
        values = self._validate_chunks(chunks)
        policy = self._policies.resolve(request.agent_role)
        claims: list[SummaryClaim] = []
        highlights: list[str] = []
        omissions: list[str] = []
        for chunk in values:
            lines = [line.strip() for line in chunk.excerpt.splitlines() if line.strip()]
            if not lines:
                continue
            if chunk.retrieval_timestamp is None or chunk.confidence is None:
                raise ValueError("evidence lacks retrieval timestamp or confidence.")
            selected = lines[0]
            actionable = [line for line in lines if _ACTIONABLE.search(line)]
            if policy.preserve_actionable and actionable:
                selected = " ".join(dict.fromkeys((selected, *actionable)))
            claim = SummaryClaim(selected, chunk.source_id, chunk.location, chunk.retrieval_timestamp, chunk.confidence)
            claims.append(claim)
            if len(highlights) < policy.highlight_limit:
                highlights.append(f"{chunk.location}: {selected}")
            if len(lines) > 1 and selected != " ".join(lines):
                omissions.append(f"{chunk.source_id}:{chunk.location}: additional excerpt lines omitted")
        summary = "\n".join(claim.text for claim in claims)
        return SummaryResult(summary, tuple(highlights), tuple(sorted(set(omissions))), tuple(claims), policy.policy_version, len(summary) > summary_budget)

    @staticmethod
    def _validate_chunks(chunks: object) -> tuple[EvidenceChunk, ...]:
        if isinstance(chunks, (str, bytes)):
            raise ValueError("chunks must be a collection of EvidenceChunk values.")
        try:
            values = tuple(chunks or ())  # type: ignore[arg-type]
        except TypeError as exc:
            raise ValueError("chunks must be a collection of EvidenceChunk values.") from exc
        if any(not isinstance(chunk, EvidenceChunk) for chunk in values):
            raise ValueError("chunks contains an invalid EvidenceChunk.")
        return tuple(sorted(values, key=lambda item: (item.source_id, item.location, item.excerpt, item.provenance)))
