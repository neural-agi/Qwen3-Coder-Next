"""Smoke tests for local tooling safe file reads."""

import tempfile
from pathlib import Path
from unittest import TestCase

from qwen3_coder_next.local_tooling import (
    DeterministicFileReadService,
    FileReadRequest,
    RepositoryWorkspaceResolver,
    WorkspaceResolutionRequest,
)


class LocalToolingReadsSmokeTest(TestCase):
    """Verify the public safe-read boundary."""

    def test_deterministic_read_service_executes(self) -> None:
        """Read a file, preview it, and compute a digest."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = RepositoryWorkspaceResolver(start_path=root).resolve(
                WorkspaceResolutionRequest(
                    request_id="read-smoke-workspace",
                    workspace_id="workspace-smoke",
                )
            ).workspace

            service = DeterministicFileReadService({root / "README.md": "alpha\nbeta\n"})
            result = service.read(
                FileReadRequest(
                    request_id="read-smoke-001",
                    workspace=workspace,
                    path="README.md",
                    preview_length=5,
                )
            )

            self.assertTrue(result.success)
            self.assertEqual(result.preview, "alpha")
