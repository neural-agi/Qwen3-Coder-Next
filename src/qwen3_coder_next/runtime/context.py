"""Runtime context for foundational service references."""

import logging
from dataclasses import dataclass

from qwen3_coder_next.adapters import ModelGateway, StubModelAdapter
from qwen3_coder_next.artifacts import ArtifactManager, ArtifactStore
from qwen3_coder_next.config import AppSettings, get_settings
from qwen3_coder_next.logging import ApplicationLogger
from qwen3_coder_next.memory import MemoryManager, MemoryStore
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
        logger=logger,
    )
