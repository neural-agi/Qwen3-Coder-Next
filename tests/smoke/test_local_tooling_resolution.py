"""Smoke tests for local tooling workspace resolution."""

import tempfile
from pathlib import Path
import unittest

from qwen3_coder_next.local_tooling import (
    RepositoryWorkspaceResolver,
    StaticWorkspaceResolver,
    WorkspaceContext,
    WorkspaceResolutionRequest,
    WorkspaceResolutionResult,
    WorkspaceResolver,
)


class LocalToolingResolutionSmokeTest(unittest.TestCase):
    """Verify workspace resolution boundary behavior."""

    def test_resolution_contracts_can_be_created(self) -> None:
        """Create the resolver request and result contracts."""

        request = WorkspaceResolutionRequest(
            request_id="resolve-001",
            workspace_id="workspace-001",
        )
        workspace = WorkspaceContext(
            workspace_id="workspace-001",
            root_path=Path("workspace"),
        )
        result = WorkspaceResolutionResult(
            request_id="resolve-001",
            workspace=workspace,
            resolved=True,
        )

        self.assertEqual(request.workspace_id, "workspace-001")
        self.assertTrue(result.resolved)
        self.assertEqual(result.workspace, workspace)

    def test_static_workspace_resolver_returns_fixed_workspace(self) -> None:
        """Resolve a workspace without filesystem discovery."""

        workspace = WorkspaceContext(
            workspace_id="workspace-002",
            root_path=Path("workspace"),
            display_name="Test Workspace",
        )
        resolver = StaticWorkspaceResolver(workspace)
        result = resolver.resolve(
            WorkspaceResolutionRequest(
                request_id="resolve-002",
                workspace_id="workspace-002",
            )
        )

        self.assertIsInstance(resolver, WorkspaceResolver)
        self.assertEqual(result.workspace, workspace)
        self.assertTrue(result.resolved)

    def test_repository_workspace_resolver_discovers_root(self) -> None:
        """Resolve a workspace from a repository-like directory layout."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            nested = root / "src" / "pkg"
            nested.mkdir(parents=True)

            resolver = RepositoryWorkspaceResolver(start_path=nested)
            result = resolver.resolve(
                WorkspaceResolutionRequest(
                    request_id="resolve-003",
                    workspace_id="workspace-003",
                )
            )

            self.assertTrue(result.resolved)
            self.assertEqual(result.workspace.root_path, root)
