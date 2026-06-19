"""Unit tests for local tooling workspace resolution."""

import tempfile
from pathlib import Path
from unittest import TestCase

from qwen3_coder_next.local_tooling import (
    RepositoryWorkspaceResolver,
    WorkspaceResolutionRequest,
)


class LocalToolingResolutionUnitTest(TestCase):
    """Verify repository root discovery and path normalization."""

    def test_repository_root_is_detected_from_actual_layout(self) -> None:
        """Resolve the nearest repository root from a nested path."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            (root / "workspace").mkdir()
            nested = root / "workspace" / "nested"
            nested.mkdir()

            resolver = RepositoryWorkspaceResolver(start_path=nested)
            result = resolver.resolve(
                WorkspaceResolutionRequest(
                    request_id="resolve-root-001",
                    workspace_id="workspace-001",
                )
            )

            self.assertTrue(result.resolved)
            self.assertIsNotNone(result.workspace)
            self.assertEqual(result.workspace.root_path, root)
            self.assertEqual(result.workspace.display_name, root.name)

    def test_path_normalization_blocks_escapes(self) -> None:
        """Reject a requested path that escapes the repository root."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()

            resolver = RepositoryWorkspaceResolver(start_path=root)
            result = resolver.resolve(
                WorkspaceResolutionRequest(
                    request_id="resolve-root-002",
                    workspace_id="workspace-002",
                    metadata={"path": "../escape.txt"},
                )
            )

            self.assertFalse(result.resolved)
            self.assertIsNone(result.workspace)
            self.assertEqual(result.metadata["reason"], "path_outside_workspace")

    def test_normalized_path_is_reported_inside_workspace(self) -> None:
        """Normalize an in-workspace relative path."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            (root / "docs").mkdir()

            resolver = RepositoryWorkspaceResolver(start_path=root)
            result = resolver.resolve(
                WorkspaceResolutionRequest(
                    request_id="resolve-root-003",
                    workspace_id="workspace-003",
                    metadata={"path": "docs/../README.md"},
                )
            )

            self.assertTrue(result.resolved)
            self.assertIsNotNone(result.workspace)
            self.assertEqual(
                result.workspace.metadata["normalized_path"],
                (root / "README.md").as_posix(),
            )
