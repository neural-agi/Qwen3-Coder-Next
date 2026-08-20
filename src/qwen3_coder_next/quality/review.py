"""Deterministic review rubric and finding extraction."""

from __future__ import annotations

from qwen3_coder_next.quality.schemas import ReviewFinding, ReviewInstruction, ReviewReport


class ReviewOrchestrator:
    """Apply a small deterministic safety rubric to a diff."""

    def review(self, instruction: ReviewInstruction, diff: str, *, worktree_id: str) -> ReviewReport:
        if not isinstance(instruction, ReviewInstruction):
            raise ValueError("instruction must be a ReviewInstruction instance.")
        if not isinstance(diff, str):
            raise ValueError("diff must be a string.")
        findings: list[ReviewFinding] = []
        if "<<<<<<<" in diff or ">>>>>>>" in diff:
            findings.append(ReviewFinding("finding-0001", "high", "merge-conflict", "Merge conflict markers remain in the diff.", instruction.diff_ref, "Resolve conflict markers."))
        if "TODO(quality-blocker)" in diff:
            findings.append(ReviewFinding("finding-0002", "high", "unfinished-work", "Quality-blocking TODO remains in the diff.", instruction.diff_ref, "Complete the blocked work."))
        status = "reject" if findings else "pass"
        return ReviewReport(instruction.task_id, worktree_id, 0.0 if findings else 1.0, tuple(findings), status, "Deterministic rubric review.")
