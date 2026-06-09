"""Smoke tests for the local tooling contract layer."""

from datetime import UTC, datetime
from pathlib import Path
import unittest

from qwen3_coder_next.local_tooling import (
    ArtifactDescriptor,
    AuditEvent,
    CommandResult,
    ExecutionPolicy,
    FileResult,
    RequestEnvelope,
    ResponseEnvelope,
    WorkspaceContext,
)


class LocalToolingContractsSmokeTest(unittest.TestCase):
    """Verify the foundational local tooling contracts."""

    def test_contract_creation(self) -> None:
        """Create all local tooling contract types."""

        policy = ExecutionPolicy(
            allow_filesystem=False,
            allow_commands=False,
            allow_network=False,
            allowed_paths=(Path("workspace"),),
        )
        workspace = WorkspaceContext(
            workspace_id="workspace-001",
            root_path=Path("workspace"),
            display_name="Test Workspace",
        )
        request = RequestEnvelope(
            request_id="request-001",
            workspace=workspace,
            operation="inspect",
            policy=policy,
        )
        response = ResponseEnvelope(
            request_id="request-001",
            success=True,
            status="ok",
        )
        file_result = FileResult(path=Path("workspace/file.txt"), exists=True)
        command_result = CommandResult(command="echo hello", exit_code=0, stdout="hello")
        descriptor = ArtifactDescriptor(
            artifact_id="artifact-001",
            name="output",
            location=Path("workspace/output.txt"),
        )
        audit = AuditEvent(
            event_id="event-001",
            timestamp=datetime.now(UTC),
            action="request.received",
            subject="request-001",
        )

        self.assertFalse(policy.allow_filesystem)
        self.assertEqual(workspace.root_path, Path("workspace"))
        self.assertEqual(request.workspace, workspace)
        self.assertTrue(response.success)
        self.assertTrue(file_result.exists)
        self.assertEqual(command_result.exit_code, 0)
        self.assertEqual(descriptor.location, Path("workspace/output.txt"))
        self.assertEqual(audit.action, "request.received")

    def test_basic_usage(self) -> None:
        """Verify the contracts compose into a simple request/response boundary."""

        policy = ExecutionPolicy()
        workspace = WorkspaceContext(workspace_id="workspace-002", root_path=Path("workspace"))
        request = RequestEnvelope(
            request_id="request-002",
            workspace=workspace,
            operation="list",
            policy=policy,
            payload={"target": "README.md"},
        )
        response = ResponseEnvelope(
            request_id=request.request_id,
            success=False,
            status="blocked",
            payload={"reason": "filesystem access disabled"},
        )

        self.assertEqual(request.operation, "list")
        self.assertEqual(request.payload["target"], "README.md")
        self.assertEqual(response.status, "blocked")
