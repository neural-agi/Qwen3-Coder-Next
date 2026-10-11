"""Deterministic budget accounting and trimming for Part 11 Step 6."""
from __future__ import annotations

from dataclasses import dataclass, field

from qwen3_coder_next.context_compression.schemas import BudgetReport, CompressionConfig, ContextRequest
from qwen3_coder_next.context_compression.summarizer import SummaryClaim, SummaryResult


_REASON_OVER_BUDGET = "over_budget"
_REASON_RESERVED_HEADROOM = "reserved_headroom"
_REASON_REQUIRED_CONTENT = "required_content_exceeds_budget"


def estimate_tokens(text: str) -> int:
    """Conservative, deterministic estimate: four UTF-8 bytes per estimated token."""
    if not isinstance(text, str):
        raise ValueError("text must be text.")
    if not text:
        return 0
    return (len(text.encode("utf-8")) + 3) // 4


@dataclass(frozen=True, slots=True)
class BudgetResult:
    accepted_claims: tuple[SummaryClaim, ...] = field(default_factory=tuple)
    rendered_summary: str = ""
    omissions: tuple[str, ...] = field(default_factory=tuple)
    report: BudgetReport = field(default_factory=lambda: BudgetReport(0, 0, 0))
    feasible: bool = True

    def __post_init__(self) -> None:
        if any(not isinstance(claim, SummaryClaim) for claim in self.accepted_claims):
            raise ValueError("accepted_claims contains an invalid SummaryClaim.")
        if not isinstance(self.rendered_summary, str):
            raise ValueError("rendered_summary must be text.")
        if any(not isinstance(item, str) or not item.strip() for item in self.omissions):
            raise ValueError("omissions must contain non-empty text.")
        if not isinstance(self.report, BudgetReport):
            raise ValueError("report must be a BudgetReport.")
        if not isinstance(self.feasible, bool):
            raise ValueError("feasible must be boolean.")
        object.__setattr__(self, "accepted_claims", tuple(self.accepted_claims))
        object.__setattr__(self, "omissions", tuple(self.omissions))


class BudgetManager:
    """Apply hard budget limits after summarization, without package assembly."""

    def apply(
        self,
        request: ContextRequest,
        summary: SummaryResult,
        requested_budget: int,
        reserved_budget: int,
        config: CompressionConfig,
    ) -> BudgetResult:
        if not isinstance(request, ContextRequest):
            raise ValueError("request must be a ContextRequest.")
        if not isinstance(summary, SummaryResult):
            raise ValueError("summary must be a SummaryResult.")
        if not isinstance(config, CompressionConfig):
            raise ValueError("config must be a CompressionConfig.")
        self._validate_budget(requested_budget, reserved_budget)
        effective_budget = min(requested_budget, config.max_tokens)
        if reserved_budget > effective_budget:
            raise ValueError("reserved_budget exceeds configured maximum budget.")
        available = effective_budget - reserved_budget
        required = self._render(request.intent)
        required_cost = estimate_tokens(required)
        if required_cost > available:
            report = BudgetReport(effective_budget, 0, reserved_budget, (), (_REASON_REQUIRED_CONTENT,))
            return BudgetResult((), "", (), report, False)

        used = required_cost
        accepted: list[SummaryClaim] = []
        omissions: list[str] = []
        for claim in summary.claims:
            rendered = self._render_claim(claim)
            cost = estimate_tokens(rendered)
            if used + cost <= available:
                accepted.append(claim)
                used += cost
            else:
                omissions.append(f"{claim.source_id}: {_REASON_RESERVED_HEADROOM if used + cost > available else _REASON_OVER_BUDGET}")
        rendered_summary = "\n".join((required, *(self._render_claim(claim) for claim in accepted)))
        report = BudgetReport(effective_budget, used, reserved_budget, tuple(sorted({claim.source_id for claim in summary.claims if claim not in accepted})), tuple(sorted(set(omissions))))
        return BudgetResult(tuple(accepted), rendered_summary, tuple(omissions), report, True)

    @staticmethod
    def _validate_budget(requested_budget: object, reserved_budget: object) -> None:
        for value, name in ((requested_budget, "requested_budget"), (reserved_budget, "reserved_budget")):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")
        if reserved_budget > requested_budget:
            raise ValueError("reserved_budget exceeds requested_budget.")

    @staticmethod
    def _render(text: str) -> str:
        return f"Intent: {text}"

    @staticmethod
    def _render_claim(claim: SummaryClaim) -> str:
        return f"[{claim.source_id}] {claim.location}: {claim.text}"
