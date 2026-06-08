"""Runtime context for foundational service references."""

import logging
from dataclasses import dataclass

from qwen3_coder_next.adapters import ModelGateway, StubModelAdapter
from qwen3_coder_next.config import AppSettings, get_settings
from qwen3_coder_next.logging import ApplicationLogger
from qwen3_coder_next.state import StateManager


RUNTIME_LOGGER_NAME = "qwen3_coder_next.runtime.orchestrator"


@dataclass(frozen=True, slots=True)
class RuntimeContext:
    """Container for foundational runtime service references."""

    settings: AppSettings
    state_manager: StateManager
    model_gateway: ModelGateway
    logger: logging.Logger


def create_runtime_context(settings: AppSettings | None = None) -> RuntimeContext:
    """Create a runtime context from foundational services."""

    resolved_settings = settings or get_settings()
    logger = ApplicationLogger.initialize(
        resolved_settings,
        logger_name=RUNTIME_LOGGER_NAME,
    )
    return RuntimeContext(
        settings=resolved_settings,
        state_manager=StateManager(),
        model_gateway=ModelGateway(StubModelAdapter()),
        logger=logger,
    )
