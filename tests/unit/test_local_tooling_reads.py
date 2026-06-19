"""Unit tests for local tooling safe file reads."""

import tempfile
from pathlib import Path
from unittest import TestCase

from qwen3_coder_next.local_tooling import (
    DeterministicFileReadService,
    FileReadErrorCode,
    FileReadRequest,
    FileReadService,
    RepositoryWorkspaceResolver,
    WorkspaceResolutionRequest,
)


class LocalToolingReadsUnitTest(TestCase):
    """Verify read-only semantics, preview, digest, and structured errors."""

    def _workspace(self, root: Path):
        resolver = RepositoryWorkspaceResolver(start_path=root)
        result = resolver.resolve(
            WorkspaceResolutionRequest(request_id="workspace-001", workspace_id="workspace-001")
        )
        self.assertTrue(result.resolved)
        self.assertIsNotNone(result.workspace)
        return result.workspace

    def test_read_request_can_be_created(self) -> None:
        """Create the read request contract."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            request = FileReadRequest(
                request_id="read-001",
                workspace=workspace,
                path=Path("docs/example.txt"),
                preview_length=5,
            )
            self.assertEqual(request.preview_length, 5)

    def test_deterministic_read_service_returns_content_preview_and_digest(self) -> None:
        """Return exact content, preview, and digest for a file within the workspace."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            file_path = root / "docs" / "example.txt"
            service = DeterministicFileReadService({file_path: "hello world\n"})

            result = service.read(
                FileReadRequest(
                    request_id="read-002",
                    workspace=workspace,
                    path=Path("docs/example.txt"),
                    preview_length=5,
                )
            )

            self.assertTrue(issubclass(DeterministicFileReadService, FileReadService))
            self.assertTrue(result.success)
            self.assertEqual(result.content, "hello world\n")
            self.assertEqual(result.preview, "hello")
            self.assertEqual(
                result.digest,
                "a948904f2f0f479b8f8197694b30184b0d2ed1c1cd2a1ec0fb85d299a192a447",
            )

    def test_missing_file_returns_structured_error(self) -> None:
        """Return a structured error for a missing file."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            service = DeterministicFileReadService()

            result = service.read(
                FileReadRequest(
                    request_id="read-003",
                    workspace=workspace,
                    path=Path("docs/missing.txt"),
                )
            )

            self.assertFalse(result.success)
            self.assertEqual(result.error_code, FileReadErrorCode.FILE_NOT_FOUND)

    def test_invalid_path_returns_structured_error(self) -> None:
        """Reject invalid input paths."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            service = DeterministicFileReadService()

            result = service.read(
                FileReadRequest(
                    request_id="read-004",
                    workspace=workspace,
                    path="",
                )
            )

            self.assertFalse(result.success)
            self.assertEqual(result.error_code, FileReadErrorCode.INVALID_PATH)

    def test_escape_attempt_returns_structured_error(self) -> None:
        """Reject a path that escapes the workspace."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            service = DeterministicFileReadService()

            result = service.read(
                FileReadRequest(
                    request_id="read-005",
                    workspace=workspace,
                    path=Path("../escape.txt"),
                )
            )

            self.assertFalse(result.success)
            self.assertEqual(result.error_code, FileReadErrorCode.PATH_OUTSIDE_WORKSPACE)
