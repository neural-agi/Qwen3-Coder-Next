"""Unit tests for the local tooling adapter layer."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest import TestCase

from qwen3_coder_next.local_tooling import (
    ArtifactProvenance,
    ArtifactRegistryResult,
    AuditLoggerResult,
    CommandResult,
    DeterministicArtifactRegistry,
    DeterministicAuditLogger,
    DeterministicCommandRunner,
    DeterministicDiffService,
    DeterministicFileMutationService,
    DeterministicFileReadService,
    DeterministicFileSystemService,
    DeterministicToolAdapter,
    ExecutionPolicy,
    FileSystemOperationResult,
    FileSystemOperationType,
    RequestEnvelope,
    ResponseEnvelope,
    RepositoryWorkspaceResolver,
    WorkspaceContext,
    WorkspaceResolutionRequest,
)


class LocalToolingAdapterUnitTest(TestCase):
    """Verify request normalization, routing, and normalized responses."""

    def _workspace(self, root: Path) -> WorkspaceContext:
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

    def _adapter(self, root: Path) -> DeterministicToolAdapter:
        workspace = self._workspace(root)
        file_path = root / "docs" / "note.txt"
        file_content = "alpha\n"
        return DeterministicToolAdapter(
            workspace_resolver=RepositoryWorkspaceResolver(start_path=root),
            file_read_service=DeterministicFileReadService({file_path: file_content}),
            filesystem_service=DeterministicFileSystemService({file_path: file_content}),
            file_mutation_service=DeterministicFileMutationService({file_path: file_content}),
            diff_service=DeterministicDiffService(),
            command_runner=DeterministicCommandRunner(
                {("echo", "hello"): CommandResult(command="echo hello", exit_code=0, stdout="hello\n")}
            ),
            artifact_registry=DeterministicArtifactRegistry(root / "artifacts.json"),
            audit_logger=DeterministicAuditLogger(root / "audit.json"),
        )

    def test_request_normalization_and_response_shape(self) -> None:
        """Normalize an alias operation into the canonical response envelope."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            adapter = self._adapter(root)

            response = adapter.handle(
                RequestEnvelope(
                    request_id="adapter-001",
                    workspace=workspace,
                    operation="  READ ",
                    policy=ExecutionPolicy(allow_filesystem=True),
                    payload={"path": Path("docs/note.txt"), "preview_length": 3},
                )
            )

            self.assertIsInstance(response, ResponseEnvelope)
            self.assertTrue(response.success)
            self.assertEqual(response.payload["operation"], "file.read")
            self.assertEqual(response.payload["service"], "file_read")
            self.assertIn("artifact", response.payload)
            self.assertIn("audit", response.payload)
            self.assertEqual(response.payload["result"]["preview"], "alp")

    def test_command_route_returns_normalized_result(self) -> None:
        """Route a command through the adapter and normalize the response."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            adapter = self._adapter(root)

            response = adapter.handle(
                RequestEnvelope(
                    request_id="adapter-002",
                    workspace=workspace,
                    operation="COMMAND.RUN",
                    policy=ExecutionPolicy(allow_commands=True),
                    payload={"command": "echo", "arguments": ("hello",), "working_directory": "."},
                )
            )

            self.assertTrue(response.success)
            self.assertEqual(response.payload["service"], "command")
            self.assertEqual(response.payload["result"]["result"]["stdout"], "hello\n")

    def test_artifact_and_audit_routes_are_exposed(self) -> None:
        """Route directly to artifact registry and audit logger services."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            adapter = self._adapter(root)

            artifact_response = adapter.handle(
                RequestEnvelope(
                    request_id="adapter-003",
                    workspace=workspace,
                    operation="artifact.register",
                    policy=ExecutionPolicy(allow_filesystem=True),
                    payload={
                        "artifact_id": "artifact-003",
                        "name": "capture",
                        "location": root / "artifacts" / "capture.txt",
                        "artifact_type": "capture",
                        "content": "payload",
                        "provenance": ArtifactProvenance(
                            request_id="adapter-003",
                            operation="artifact.register",
                            source="unit-test",
                            timestamp=datetime.now(UTC),
                        ),
                    },
                )
            )
            audit_response = adapter.handle(
                RequestEnvelope(
                    request_id="adapter-004",
                    workspace=workspace,
                    operation="audit.append",
                    policy=ExecutionPolicy(),
                    payload={
                        "action": "tool.run",
                        "subject": "capture",
                        "status": "ok",
                    },
                )
            )

            self.assertTrue(artifact_response.success)
            self.assertTrue(audit_response.success)
            self.assertIsInstance(artifact_response.payload["result"]["manifest"], dict)
            self.assertIsInstance(audit_response.payload["result"]["record"], dict)
