"""Minimal task execution framework for the foundation layer."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from qwen3_coder_next.artifacts import ArtifactManager
from qwen3_coder_next.contracts import ModelRequest, TaskRequest, TaskState, TaskStatus
from qwen3_coder_next.execution.result import ExecutionResult
from qwen3_coder_next.runtime import Orchestrator


class Executor:
    """Coordinate a minimal task lifecycle across foundation services."""

    def __init__(
        self,
        orchestrator: Orchestrator,
        artifact_manager: ArtifactManager | None = None,
    ) -> None:
        """Initialize the executor with foundational services."""

        self._orchestrator = orchestrator
        self._artifact_manager = artifact_manager or ArtifactManager()
        self._state_manager = orchestrator.context.state_manager
        self._model_gateway = orchestrator.context.model_gateway
        self._logger = orchestrator.context.logger

    @property
    def artifact_manager(self) -> ArtifactManager:
        """Return the artifact manager bound to this executor."""

        return self._artifact_manager

    def execute(self, task: str | TaskRequest) -> ExecutionResult:
        """Execute a minimal task lifecycle without agent behavior."""

        request = self._normalize_request(task)
        self._logger.info("Task execution started: task_id=%s", request.task_id)

        current_time = datetime.now(UTC)
        current_state = self._state_manager.create_state(
            TaskState(
                task_id=request.task_id,
                status=TaskStatus.PENDING,
                created_at=current_time,
                updated_at=current_time,
            )
        )

        running_state = replace(
            current_state,
            status=TaskStatus.RUNNING,
            updated_at=datetime.now(UTC),
        )
        self._state_manager.update_state(running_state)

        self._model_gateway.generate(
            ModelRequest(
                prompt=request.objective,
                system_prompt="Foundation execution stub",
            )
        )
        summary = self._orchestrator.execute(request.objective)

        succeeded_state = replace(
            running_state,
            status=TaskStatus.SUCCEEDED,
            updated_at=datetime.now(UTC),
        )
        self._state_manager.update_state(succeeded_state)

        self._logger.info("Task execution completed: task_id=%s", request.task_id)
        return ExecutionResult(
            task_id=request.task_id,
            success=True,
            summary=summary,
        )

    def _normalize_request(self, task: str | TaskRequest) -> TaskRequest:
        """Normalize executor input into a task request."""

        if isinstance(task, TaskRequest):
            return task
        return TaskRequest(
            task_id=f"task-{uuid4()}",
            objective=task,
        )
