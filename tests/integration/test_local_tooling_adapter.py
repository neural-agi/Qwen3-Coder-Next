"""Integration tests for the local tooling adapter layer."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest import TestCase

from qwen3_coder_next.local_tooling import (
    ArtifactProvenance,
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
    FileMutationType,
    FileSystemOperationType,
    RepositoryWorkspaceResolver,
    RequestEnvelope,
    WorkspaceResolutionRequest,
)


class LocalToolingAdapterIntegrationTest(TestCase):
    """Verify the complete adapter flow across the local tooling boundary."""

    def test_end_to_end_request_flow(self) -> None:
        """Exercise request normalization, routing, capture, and audit logging."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            file_path = root / "docs" / "note.txt"
            file_path.parent.mkdir(parents=True)
            content = "alpha\n"

            workspace_resolver = RepositoryWorkspaceResolver(start_path=root)
            workspace = workspace_resolver.resolve(
                WorkspaceResolutionRequest(
                    request_id="workspace-flow-001",
                    workspace_id="workspace-flow-001",
                )
            ).workspace
            assert workspace is not None

            adapter = DeterministicToolAdapter(
                workspace_resolver=workspace_resolver,
                file_read_service=DeterministicFileReadService({file_path: content}),
                filesystem_service=DeterministicFileSystemService({file_path: content}),
                file_mutation_service=DeterministicFileMutationService({file_path: content}),
                diff_service=DeterministicDiffService(),
                command_runner=DeterministicCommandRunner(
                    {("echo", "hello"): CommandResult(command="echo hello", exit_code=0, stdout="hello\n")}
                ),
                artifact_registry=DeterministicArtifactRegistry(root / "artifacts.json"),
                audit_logger=DeterministicAuditLogger(root / "audit.json"),
            )

            read_response = adapter.handle(
                RequestEnvelope(
                    request_id="flow-001",
                    workspace=workspace,
                    operation="READ",
                    policy=ExecutionPolicy(allow_filesystem=True),
                    payload={"path": Path("docs/note.txt"), "preview_length": 4},
                )
            )
            fs_response = adapter.handle(
                RequestEnvelope(
                    request_id="flow-002",
                    workspace=workspace,
                    operation="filesystem.operation",
                    policy=ExecutionPolicy(allow_filesystem=True),
                    payload={
                        "operation_type": FileSystemOperationType.WRITE,
                        "path": Path("docs/note.txt"),
                        "content": "beta\n",
                    },
                )
            )
            mutation_response = adapter.handle(
                RequestEnvelope(
                    request_id="flow-003",
                    workspace=workspace,
                    operation="filesystem.mutation",
                    policy=ExecutionPolicy(allow_filesystem=True),
                    payload={
                        "mutation_type": FileMutationType.APPEND,
                        "path": Path("docs/note.txt"),
                        "content": "gamma\n",
                    },
                )
            )
            diff_response = adapter.handle(
                RequestEnvelope(
                    request_id="flow-004",
                    workspace=workspace,
                    operation="diff.generate",
                    policy=ExecutionPolicy(allow_filesystem=True),
                    payload={
                        "path": Path("docs/note.txt"),
                        "before": "alpha\n",
                        "after": "beta\n",
                    },
                )
            )
            command_response = adapter.handle(
                RequestEnvelope(
                    request_id="flow-005",
                    workspace=workspace,
                    operation="command.run",
                    policy=ExecutionPolicy(allow_commands=True),
                    payload={
                        "command": "echo",
                        "arguments": ("hello",),
                        "working_directory": ".",
                    },
                )
            )
            artifact_response = adapter.handle(
                RequestEnvelope(
                    request_id="flow-006",
                    workspace=workspace,
                    operation="artifact.register",
                    policy=ExecutionPolicy(allow_filesystem=True),
                    payload={
                        "artifact_id": "flow-artifact",
                        "name": "capture",
                        "location": root / "artifacts" / "capture.txt",
                        "artifact_type": "capture",
                        "content": "payload",
                        "provenance": ArtifactProvenance(
                            request_id="flow-006",
                            operation="artifact.register",
                            source="integration-test",
                            timestamp=datetime.now(UTC),
                        ),
                    },
                )
            )
            audit_response = adapter.handle(
                RequestEnvelope(
                    request_id="flow-007",
                    workspace=workspace,
                    operation="audit.append",
                    policy=ExecutionPolicy(),
                    payload={
                        "action": "tool.run",
                        "subject": "flow-artifact",
                        "status": "ok",
                    },
                )
            )

            self.assertTrue(read_response.success)
            self.assertTrue(fs_response.success)
            self.assertTrue(mutation_response.success)
            self.assertTrue(diff_response.success)
            self.assertTrue(command_response.success)
            self.assertTrue(artifact_response.success)
            self.assertTrue(audit_response.success)
            self.assertEqual(read_response.payload["service"], "file_read")
            self.assertEqual(fs_response.payload["service"], "filesystem_operation")
            self.assertEqual(mutation_response.payload["service"], "filesystem_mutation")
            self.assertEqual(diff_response.payload["service"], "diff")
            self.assertEqual(command_response.payload["service"], "command")
            self.assertEqual(artifact_response.payload["service"], "artifact_registry")
            self.assertEqual(audit_response.payload["service"], "audit_logger")
            self.assertEqual(len(DeterministicArtifactRegistry(root / "artifacts.json").list()), 6)
            self.assertEqual(len(DeterministicAuditLogger(root / "audit.json").list()), 6)
