"""Unit tests for local tooling command runner support."""

import tempfile
from pathlib import Path
from unittest import TestCase

from qwen3_coder_next.local_tooling import (
    CommandRequest,
    CommandResult,
    CommandRunErrorCode,
    CommandRunner,
    DeterministicCommandRunner,
    RepositoryWorkspaceResolver,
    WorkspaceResolutionRequest,
)


class LocalToolingCommandsUnitTest(TestCase):
    """Verify controlled command execution and structured rejection cases."""

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

    def test_command_request_can_be_created(self) -> None:
        """Create the command request contract."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)

            request = CommandRequest(
                request_id="cmd-001",
                workspace=workspace,
                command="echo",
                arguments=("hello",),
                working_directory=Path("tools"),
            )

            self.assertEqual(request.command, "echo")
            self.assertEqual(request.arguments, ("hello",))

    def test_deterministic_runner_executes_allowlisted_command(self) -> None:
        """Return a configured command result without shell execution."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            runner = DeterministicCommandRunner(
                {
                    ("echo", "hello"): CommandResult(
                        command="echo hello",
                        exit_code=0,
                        stdout="hello\n",
                    )
                }
            )

            self.assertTrue(issubclass(DeterministicCommandRunner, CommandRunner))
            result = runner.run(
                CommandRequest(
                    request_id="cmd-002",
                    workspace=workspace,
                    command="echo",
                    arguments=("hello",),
                    working_directory=Path("tools"),
                )
            )

            self.assertTrue(result.allowed)
            self.assertIsNotNone(result.result)
            self.assertEqual(result.result.stdout, "hello\n")
            self.assertEqual(result.result.metadata["working_directory"], (root / "tools").resolve().as_posix())

    def test_disallowed_command_returns_structured_error(self) -> None:
        """Reject commands that are not on the allowlist."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            runner = DeterministicCommandRunner()

            result = runner.run(
                CommandRequest(
                    request_id="cmd-003",
                    workspace=workspace,
                    command="rm",
                    arguments=("-rf", "."),
                )
            )

            self.assertFalse(result.allowed)
            self.assertEqual(result.error_code, CommandRunErrorCode.COMMAND_NOT_ALLOWED)

    def test_working_directory_escape_is_rejected(self) -> None:
        """Reject explicit working directories that escape the workspace."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            runner = DeterministicCommandRunner(
                {
                    ("echo", "hello"): CommandResult(
                        command="echo hello",
                        exit_code=0,
                        stdout="hello\n",
                    )
                }
            )

            result = runner.run(
                CommandRequest(
                    request_id="cmd-004",
                    workspace=workspace,
                    command="echo",
                    arguments=("hello",),
                    working_directory=Path("../escape"),
                )
            )

            self.assertFalse(result.allowed)
            self.assertEqual(result.error_code, CommandRunErrorCode.WORKING_DIRECTORY_OUTSIDE_WORKSPACE)

    def test_invalid_command_is_rejected(self) -> None:
        """Reject malformed command strings."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            runner = DeterministicCommandRunner()

            result = runner.run(
                CommandRequest(
                    request_id="cmd-005",
                    workspace=workspace,
                    command="",
                )
            )

            self.assertFalse(result.allowed)
            self.assertEqual(result.error_code, CommandRunErrorCode.INVALID_COMMAND)

