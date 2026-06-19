"""Unit tests for local tooling safe writes and patches."""

import tempfile
from pathlib import Path
from unittest import TestCase

from qwen3_coder_next.local_tooling import (
    DeterministicFileMutationService,
    FileMutationPreflightResult,
    FileMutationRequest,
    FileMutationService,
    FileMutationType,
    RepositoryWorkspaceResolver,
    WorkspaceResolutionRequest,
)


class LocalToolingMutationsUnitTest(TestCase):
    """Verify atomic writes, append operations, patch application, and preflight checks."""

    def _workspace(self, root: Path):
        resolver = RepositoryWorkspaceResolver(start_path=root)
        result = resolver.resolve(
            WorkspaceResolutionRequest(
                request_id="workspace-001",
                workspace_id="workspace-001",
            )
        )
        self.assertTrue(result.resolved)
        self.assertIsNotNone(result.workspace)
        return result.workspace

    def test_mutation_request_can_be_created(self) -> None:
        """Create the mutation request contract."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)

            request = FileMutationRequest(
                request_id="mut-001",
                workspace=workspace,
                path=Path("docs/example.txt"),
                mutation_type=FileMutationType.ATOMIC_WRITE,
                content="hello",
            )

            self.assertEqual(request.content, "hello")

    def test_atomic_write_is_deterministic(self) -> None:
        """Write content atomically within the workspace boundary."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            service = DeterministicFileMutationService()

            result = service.apply(
                FileMutationRequest(
                    request_id="mut-002",
                    workspace=workspace,
                    path="docs/example.txt",
                    mutation_type=FileMutationType.ATOMIC_WRITE,
                    content="alpha\n",
                )
            )

            self.assertTrue(issubclass(DeterministicFileMutationService, FileMutationService))
            self.assertTrue(result.success)
            self.assertEqual(result.content, "alpha\n")
            self.assertEqual(result.previous_content, "")

    def test_append_operation_appends_to_existing_content(self) -> None:
        """Append content without mutating the prior text unexpectedly."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            service = DeterministicFileMutationService()

            service.apply(
                FileMutationRequest(
                    request_id="mut-003",
                    workspace=workspace,
                    path=Path("docs/example.txt"),
                    mutation_type=FileMutationType.ATOMIC_WRITE,
                    content="alpha\n",
                )
            )
            result = service.apply(
                FileMutationRequest(
                    request_id="mut-004",
                    workspace=workspace,
                    path=Path("docs/example.txt"),
                    mutation_type=FileMutationType.APPEND,
                    content="beta\n",
                )
            )

            self.assertTrue(result.success)
            self.assertEqual(result.content, "alpha\nbeta\n")
            self.assertEqual(result.previous_content, "alpha\n")

    def test_patch_application_requires_expected_content(self) -> None:
        """Apply a patch only when the expected content matches the current content."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            service = DeterministicFileMutationService(
                {root / "docs" / "example.txt": "alpha\n"}
            )

            result = service.apply(
                FileMutationRequest(
                    request_id="mut-005",
                    workspace=workspace,
                    path=Path("docs/example.txt"),
                    mutation_type=FileMutationType.PATCH,
                    expected_content="alpha\n",
                    content="beta\n",
                )
            )

            self.assertTrue(result.success)
            self.assertEqual(result.content, "beta\n")
            self.assertEqual(result.previous_content, "alpha\n")

    def test_patch_application_rejects_mismatch(self) -> None:
        """Reject a patch when the expected content does not match."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            service = DeterministicFileMutationService(
                {root / "docs" / "example.txt": "alpha\n"}
            )

            result = service.apply(
                FileMutationRequest(
                    request_id="mut-006",
                    workspace=workspace,
                    path=Path("docs/example.txt"),
                    mutation_type=FileMutationType.PATCH,
                    expected_content="wrong\n",
                    content="beta\n",
                )
            )

            self.assertFalse(result.success)
            self.assertIsNotNone(result.preflight)
            self.assertFalse(result.preflight.allowed)

    def test_preflight_rejects_escape_attempts(self) -> None:
        """Reject paths that escape the workspace boundary."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            service = DeterministicFileMutationService()

            preflight = service.preflight(
                FileMutationRequest(
                    request_id="mut-007",
                    workspace=workspace,
                    path=Path("../escape.txt"),
                    mutation_type=FileMutationType.ATOMIC_WRITE,
                    content="x",
                )
            )

            self.assertFalse(preflight.allowed)
            self.assertEqual(preflight.error_code, "path_outside_workspace")

    def test_preflight_rejects_unsupported_inputs(self) -> None:
        """Reject unsupported path input types."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            service = DeterministicFileMutationService()

            preflight = service.preflight(
                FileMutationRequest(
                    request_id="mut-008",
                    workspace=workspace,
                    path=123,  # type: ignore[arg-type]
                    mutation_type=FileMutationType.ATOMIC_WRITE,
                    content="x",
                )
            )

            self.assertFalse(preflight.allowed)
            self.assertEqual(preflight.error_code, "unsupported_input")
