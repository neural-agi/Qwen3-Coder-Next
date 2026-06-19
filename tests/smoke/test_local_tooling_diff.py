"""Smoke tests for local tooling diff generation."""

from pathlib import Path
from unittest import TestCase

from qwen3_coder_next.local_tooling import DeterministicDiffService, DiffRequest


class LocalToolingDiffSmokeTest(TestCase):
    """Verify the diff service works end-to-end for a simple change set."""

    def test_deterministic_diff_service_executes(self) -> None:
        """Generate a diff for a simple content change."""

        service = DeterministicDiffService()
        result = service.generate_diff(
            DiffRequest(
                request_id="diff-smoke-001",
                path=Path("docs/example.txt"),
                before="one\n",
                after="two\n",
            )
        )

        self.assertTrue(result.has_changes)
        self.assertTrue(result.diff_text.startswith("--- docs/example.txt (before)"))
