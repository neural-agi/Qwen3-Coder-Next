"""Command runner abstractions for the local tooling layer."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from qwen3_coder_next.local_tooling.contracts import CommandResult, WorkspaceContext


class CommandRunErrorCode(StrEnum):
    """Structured error codes for safe command execution."""

    INVALID_COMMAND = "invalid_command"
    COMMAND_NOT_ALLOWED = "command_not_allowed"
    INVALID_WORKING_DIRECTORY = "invalid_working_directory"
    WORKING_DIRECTORY_OUTSIDE_WORKSPACE = "working_directory_outside_workspace"
    UNSUPPORTED_INPUT = "unsupported_input"


@dataclass(frozen=True, slots=True)
class CommandRequest:
    """Immutable request for running a controlled command."""

    request_id: str
    workspace: WorkspaceContext
    command: str
    arguments: tuple[str, ...] = ()
    working_directory: Path | str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CommandRunResult:
    """Immutable result returned by a command runner."""

    request_id: str
    path: Path
    allowed: bool
    result: CommandResult | None = None
    error_code: CommandRunErrorCode | None = None
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class CommandRunner(ABC):
    """Abstract command runner interface."""

    @abstractmethod
    def run(self, request: CommandRequest) -> CommandRunResult:
        """Run a controlled command for the supplied request."""


class DeterministicCommandRunner(CommandRunner):
    """Deterministic in-memory command runner with an allowlist boundary."""

    def __init__(
        self,
        allowed_commands: dict[tuple[str, ...], CommandResult] | None = None,
    ) -> None:
        self._allowed_commands = dict(allowed_commands or {})

    def run(self, request: CommandRequest) -> CommandRunResult:
        """Return a deterministic result for an allowlisted command."""

        validation_error = self._validate_request(request)
        if validation_error is not None:
            return validation_error

        working_directory = self._resolve_working_directory(
            request.workspace.root_path,
            request.working_directory,
        )
        if working_directory is None:
            return CommandRunResult(
                request_id=request.request_id,
                path=request.workspace.root_path,
                allowed=False,
                error_code=CommandRunErrorCode.WORKING_DIRECTORY_OUTSIDE_WORKSPACE,
                error_message="Working directory escapes the workspace boundary.",
                metadata=request.metadata,
            )

        command_key = self._command_key(request.command, request.arguments)
        if command_key not in self._allowed_commands:
            return CommandRunResult(
                request_id=request.request_id,
                path=working_directory,
                allowed=False,
                error_code=CommandRunErrorCode.COMMAND_NOT_ALLOWED,
                error_message="Command is not allowlisted.",
                metadata=request.metadata,
            )

        configured_result = self._allowed_commands[command_key]
        result = CommandResult(
            command=self._render_command(command_key),
            exit_code=configured_result.exit_code,
            stdout=configured_result.stdout,
            stderr=configured_result.stderr,
            metadata={
                **configured_result.metadata,
                **request.metadata,
                "working_directory": working_directory.as_posix(),
            },
        )
        return CommandRunResult(
            request_id=request.request_id,
            path=working_directory,
            allowed=True,
            result=result,
            metadata=request.metadata,
        )

    def _validate_request(self, request: CommandRequest) -> CommandRunResult | None:
        if not isinstance(request.command, str) or not request.command.strip() or "\x00" in request.command:
            return CommandRunResult(
                request_id=request.request_id,
                path=request.workspace.root_path,
                allowed=False,
                error_code=CommandRunErrorCode.INVALID_COMMAND,
                error_message="Command must be a non-empty string.",
                metadata=request.metadata,
            )
        if not isinstance(request.arguments, tuple):
            return CommandRunResult(
                request_id=request.request_id,
                path=request.workspace.root_path,
                allowed=False,
                error_code=CommandRunErrorCode.UNSUPPORTED_INPUT,
                error_message="Arguments must be provided as a tuple of strings.",
                metadata=request.metadata,
            )
        if any(not isinstance(argument, str) for argument in request.arguments):
            return CommandRunResult(
                request_id=request.request_id,
                path=request.workspace.root_path,
                allowed=False,
                error_code=CommandRunErrorCode.UNSUPPORTED_INPUT,
                error_message="Arguments must be provided as a tuple of strings.",
                metadata=request.metadata,
            )
        return None

    def _resolve_working_directory(
        self,
        workspace_root: Path,
        working_directory: Path | str | None,
    ) -> Path | None:
        candidate = workspace_root if working_directory is None else Path(str(working_directory))
        if not candidate.is_absolute():
            candidate = workspace_root / candidate
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(workspace_root)
        except ValueError:
            return None
        return resolved

    def _command_key(self, command: str, arguments: tuple[str, ...]) -> tuple[str, ...]:
        return (command, *arguments)

    def _render_command(self, command_key: tuple[str, ...]) -> str:
        return " ".join(command_key)
