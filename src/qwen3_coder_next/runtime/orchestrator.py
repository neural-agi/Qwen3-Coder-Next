"""Foundational orchestration shell."""

from dataclasses import dataclass

from qwen3_coder_next.config import AppSettings
from qwen3_coder_next.planning import PlannerRequest
from qwen3_coder_next.runtime.context import PlanningPipelineResult, RuntimeContext, create_runtime_context


@dataclass(frozen=True, slots=True)
class PlanningRuntimeResult:
    """Structured planning output surfaced through the runtime shell."""

    pipeline: PlanningPipelineResult

    @property
    def serialized_plan_graph(self) -> str:
        """Compatibility alias for the pipeline's canonical serialized graph."""

        return self.pipeline.serialized_graph


class Orchestrator:
    """Coordinate foundational services without executing future agent logic."""

    def __init__(self, context: RuntimeContext) -> None:
        """Initialize the orchestrator with a runtime context."""

        self._context = context
        self._last_planning_result: PlanningRuntimeResult | None = None

    @classmethod
    def initialize(cls, settings: AppSettings | None = None) -> "Orchestrator":
        """Initialize foundation services and return an orchestrator."""

        return cls(create_runtime_context(settings))

    @property
    def context(self) -> RuntimeContext:
        """Return the runtime context used by the orchestrator."""

        return self._context

    @property
    def last_planning_result(self) -> PlanningRuntimeResult | None:
        """Return the most recent runtime planning result, if any."""

        return self._last_planning_result

    def plan(self, request: str | PlannerRequest) -> PlanningRuntimeResult:
        """Run the deterministic planning pipeline through the runtime."""

        pipeline = self._context.plan_request(request)
        self._last_planning_result = PlanningRuntimeResult(
            pipeline=pipeline,
        )
        return self._last_planning_result

    def execute(self, task_name: str) -> str:
        """Run the placeholder orchestration shell for a task name."""

        self._context.logger.info("Orchestration execution started: task_name=%s", task_name)
        self.plan(task_name)
        result = f"Orchestration shell completed for task: {task_name}"
        self._context.logger.info("Orchestration execution finished: task_name=%s", task_name)
        return result
