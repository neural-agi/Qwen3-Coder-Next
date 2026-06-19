"""Smoke tests for local tooling command runner support."""

import tempfile
from pathlib import Path
from unittest import TestCase

from qwen3_coder_next.local_tooling import (
    CommandRequest,
    CommandResult,
    DeterministicCommandRunner,
    RepositoryWorkspaceResolver,
    WorkspaceResolutionRequest,
)


class LocalToolingCommandsSmokeTest(TestCase):
    """Verify the public command runner boundary executes deterministically."""

    def test_deterministic_command_runner_executes(self) -> None:
        """Run an allowlisted command and capture the configured output."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = RepositoryWorkspaceResolver(start_path=root).resolve(
                WorkspaceResolutionRequest(
                    request_id="cmd-smoke-workspace",
                    workspace_id="workspace-smoke",
                )
            ).workspace

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
                    request_id="cmd-smoke-001",
                    workspace=workspace,
                    command="echo",
                    arguments=("hello",),
                    working_directory=Path("tools"),
                )
            )

            self.assertTrue(result.allowed)
            self.assertEqual(result.result.stdout, "hello\n")

