"""Runtime context for foundational service references."""

import logging
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

from qwen3_coder_next.adapters import ModelGateway, StubModelAdapter
from qwen3_coder_next.artifacts import ArtifactManager, ArtifactStore
from qwen3_coder_next.config import AppSettings, get_settings
from qwen3_coder_next.logging import ApplicationLogger
from qwen3_coder_next.memory import MemoryManager, MemoryStore

from qwen3_coder_next.planning import (
    PlanArtifact,
    PlanArtifactBuilder,
    DependencyResolver,
    DecompositionEngine,
    PlanDraft,
    PlanGraph,
    PlanValidator,
    PlannerRequest,
    PlannerRequestNormalizer,
    PlannerState,
    PlanningArtifactSerializer,
    ValidationReport,
    serialize_plan_draft,
    serialize_plan_graph,
    serialize_planner_request,
    serialize_planner_state,
    serialize_validation_report,
)
from qwen3_coder_next.state import StateManager, StateStore


RUNTIME_LOGGER_NAME = "qwen3_coder_next.runtime.orchestrator"


@dataclass(frozen=True, slots=True)
class RuntimeContext:
    """Container for foundational runtime service references."""

    settings: AppSettings
    state_manager: StateManager
    artifact_manager: ArtifactManager
    memory_manager: MemoryManager
    model_gateway: ModelGateway
    logger: logging.Logger
    planner_request_normalizer: PlannerRequestNormalizer = field(
        default_factory=PlannerRequestNormalizer
    )
    decomposition_engine: DecompositionEngine = field(default_factory=DecompositionEngine)
    dependency_resolver: DependencyResolver = field(default_factory=DependencyResolver)
    plan_validator: PlanValidator = field(default_factory=PlanValidator)
    planning_serializer: PlanningArtifactSerializer = field(
        default_factory=PlanningArtifactSerializer
    )
    planning_artifact_builder: PlanArtifactBuilder = field(
        default_factory=PlanArtifactBuilder
    )

    def plan_request(
        self,
        request: str | PlannerRequest | dict[str, Any],
    ) -> "PlanningPipelineResult":
        """Run the deterministic planning pipeline for a request."""

        normalized = (
            self.planner_request_normalizer.normalize(request).request
            if not isinstance(request, PlannerRequest)
            else request
        )
        draft = self.decomposition_engine.decompose(normalized)
        graph = self.dependency_resolver.resolve(draft)
        report = self.plan_validator.validate(graph)
        artifact = self.planning_artifact_builder.build(normalized, graph, report)
        serialized_request = serialize_planner_request(normalized)
        serialized_draft = serialize_plan_draft(draft)
        serialized_graph = serialize_plan_graph(graph)
        serialized_report = serialize_validation_report(report)
        serialized_artifact = self.planning_serializer.serialize(artifact)
        deterministic_timestamp = datetime.fromtimestamp(0, UTC)
        planner_state = (
            PlannerState(
                state_id=f"{normalized.task_id}-planner-state",
                created_at=deterministic_timestamp,
                updated_at=deterministic_timestamp,
            )
            .with_current_request(normalized)
            .with_plan_draft(draft)
            .with_plan_draft(graph)
            .with_validated_plan(artifact)
        )
        planner_state = replace(
            planner_state,
            state_id=f"{normalized.task_id}-planner-state",
            created_at=deterministic_timestamp,
            updated_at=deterministic_timestamp,
            revision_history=tuple(
                replace(revision, created_at=deterministic_timestamp)
                for revision in planner_state.revision_history
            ),
        )
        return PlanningPipelineResult(
            request=normalized,
            draft=draft,
            graph=graph,
            validation_report=report,
            artifact=artifact,
            serialized_request=serialized_request,
            serialized_draft=serialized_draft,
            serialized_graph=serialized_graph,
            serialized_validation_report=serialized_report,
            serialized_artifact=serialized_artifact,
            serialized_state=serialize_planner_state(planner_state),
        )


@dataclass(frozen=True, slots=True)
class PlanningPipelineResult:
    """Structured result returned by the runtime planning pipeline."""

    request: PlannerRequest
    draft: PlanDraft
    graph: PlanGraph
    validation_report: ValidationReport
    artifact: PlanArtifact
    serialized_request: str
    serialized_draft: str
    serialized_graph: str
    serialized_validation_report: str
    serialized_artifact: str
    serialized_state: str


def create_runtime_context(settings: AppSettings | None = None) -> RuntimeContext:
    """Create a runtime context from foundational services."""

    resolved_settings = settings or get_settings()
    logger = ApplicationLogger.initialize(
        resolved_settings,
        logger_name=RUNTIME_LOGGER_NAME,
    )
    state_store = StateStore(resolved_settings.data_dir / "state.json")
    artifact_store = ArtifactStore(resolved_settings.artifacts_dir / "artifacts.json")
    memory_store = MemoryStore(resolved_settings.data_dir / "memory.json")
    return RuntimeContext(
        settings=resolved_settings,
        state_manager=StateManager(state_store),
        artifact_manager=ArtifactManager(artifact_store),
        memory_manager=MemoryManager(memory_store),
        model_gateway=ModelGateway(StubModelAdapter()),
        planner_request_normalizer=PlannerRequestNormalizer(),
        decomposition_engine=DecompositionEngine(),
        dependency_resolver=DependencyResolver(),
        plan_validator=PlanValidator(),
        planning_serializer=PlanningArtifactSerializer(),
        planning_artifact_builder=PlanArtifactBuilder(),
        logger=logger,
    )
