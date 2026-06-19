"""Unit tests for local tooling diff generation."""

from pathlib import Path
from unittest import TestCase

from qwen3_coder_next.local_tooling import (
    DeterministicDiffService,
    DiffRequest,
    DiffService,
)


class LocalToolingDiffUnitTest(TestCase):
    """Verify diff request/result shape and deterministic output."""

    def test_diff_request_can_be_created(self) -> None:
        """Create a diff request contract."""

        request = DiffRequest(
            request_id="diff-001",
            path=Path("docs/example.txt"),
            before="hello\n",
            after="hello world\n",
        )

        self.assertEqual(request.before, "hello\n")

    def test_deterministic_diff_service_generates_stable_diff(self) -> None:
        """Generate a unified diff with deterministic text output."""

        self.assertTrue(issubclass(DeterministicDiffService, DiffService))

        service = DeterministicDiffService()
        request = DiffRequest(
            request_id="diff-002",
            path=Path("docs/example.txt"),
            before="alpha\n",
            after="beta\n",
        )

        result = service.generate_diff(request)

        self.assertTrue(result.has_changes)
        self.assertIn("--- docs/example.txt (before)", result.diff_text)
        self.assertIn("+++ docs/example.txt (after)", result.diff_text)
        self.assertIn("-alpha", result.diff_text)
        self.assertIn("+beta", result.diff_text)

    def test_identical_input_produces_empty_diff(self) -> None:
        """Return no diff text when inputs are identical."""

        service = DeterministicDiffService()
        request = DiffRequest(
            request_id="diff-003",
            path=Path("docs/example.txt"),
            before="same\n",
            after="same\n",
        )

        result = service.generate_diff(request)

        self.assertFalse(result.has_changes)
        self.assertEqual(result.diff_text, "")
