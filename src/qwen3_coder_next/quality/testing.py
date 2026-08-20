"""Test command execution and deterministic result normalization."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

from qwen3_coder_next.quality.schemas import TestInvocation, TestReport


@dataclass(frozen=True, slots=True)
class RawTestResult:
    exit_code: int
    output: str
    timed_out: bool = False


class TestOrchestrator:
    """Launch one explicitly supplied command in an isolated worktree."""

    def run(self, invocation: TestInvocation) -> RawTestResult:
        if not isinstance(invocation, TestInvocation):
            raise ValueError("invocation must be a TestInvocation instance.")
        try:
            completed = subprocess.run(
                list(invocation.command), cwd=invocation.cwd, capture_output=True,
                text=True, timeout=invocation.timeout, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            output = (exc.stdout or "") + (exc.stderr or "")
            return RawTestResult(exit_code=-1, output=output, timed_out=True)
        return RawTestResult(completed.returncode, completed.stdout + completed.stderr)


class ResultNormalizer:
    """Normalize standard unittest output into a stable report."""

    def normalize(self, invocation: TestInvocation, raw: RawTestResult, *, suite_name: str) -> TestReport:
        if not isinstance(invocation, TestInvocation) or not isinstance(raw, RawTestResult):
            raise ValueError("invocation and raw must use the quality contracts.")
        if not isinstance(suite_name, str) or not suite_name.strip():
            raise ValueError("suite_name must be a non-empty string.")
        matches = re.findall(r"^(?:FAIL|ERROR):\s*(\S+)", raw.output, re.MULTILINE)
        failed_names = tuple(sorted(set(matches)))
        status = "timeout" if raw.timed_out else ("pass" if raw.exit_code == 0 else "fail")
        summary_match = re.search(r"Ran\s+(\d+)\s+tests?.*", raw.output)
        summary = f"{summary_match.group(1)} tests, status={status}" if summary_match else f"status={status}"
        return TestReport(invocation.task_id, invocation.worktree_id, suite_name, raw.exit_code, status, summary, failed_names)
