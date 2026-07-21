"""Foundational orchestration shell."""

from dataclasses import dataclass

from qwen3_coder_next.config import AppSettings
from qwen3_coder_next.memory import MemoryState
from qwen3_coder_next.contracts import TaskRequest
from qwen3_coder_next.memory import MemoryItem
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
    def active_task_id(self) -> str | None:
        """Return the currently active task identifier, if any."""

        return self._context.active_task_id

    @property
    def working_memory(self) -> MemoryState:
        """Return the current transient working-memory snapshot."""

        return self._context.get_working_memory_snapshot()

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

    def activate_task(self, task_request: TaskRequest) -> None:
        """Reset the transient working memory for a new task."""

        self._context = self._context.activate_task(task_request)

    def append_working_memory_item(self, memory_item: MemoryItem) -> MemoryState:
        """Append an item to the transient working-memory snapshot."""

        self._context = self._context.append_working_memory_item(memory_item)
        return self._context.get_working_memory_snapshot()

    def execute(self, task_name: str) -> str:
        """Run the placeholder orchestration shell for a task name."""

        self._context.logger.info("Orchestration execution started: task_name=%s", task_name)
        self.plan(task_name)
        result = f"Orchestration shell completed for task: {task_name}"
        self._context.logger.info("Orchestration execution finished: task_name=%s", task_name)
        return result
