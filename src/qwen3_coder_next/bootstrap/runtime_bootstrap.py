"""Runtime bootstrap composition for foundational services."""

import logging
from dataclasses import dataclass

from qwen3_coder_next.config import AppSettings, get_settings
from qwen3_coder_next.logging import ApplicationLogger
from qwen3_coder_next.runtime import (
    Orchestrator,
    RUNTIME_LOGGER_NAME,
    RuntimeContext,
    create_runtime_context,
)


BOOTSTRAP_LOGGER_NAME = "qwen3_coder_next.bootstrap.runtime"


@dataclass(frozen=True, slots=True)
class RuntimeBootstrap:
    """Bootstrap container for foundational runtime services."""

    settings: AppSettings
    logger: logging.Logger
    context: RuntimeContext
    orchestrator: Orchestrator

    @classmethod
    def initialize(cls, settings: AppSettings | None = None) -> "RuntimeBootstrap":
        """Create the foundational runtime bootstrap."""

        resolved_settings = settings or get_settings()
        logger = ApplicationLogger.initialize(
            resolved_settings,
            logger_name=BOOTSTRAP_LOGGER_NAME,
        )
        context = create_runtime_context(resolved_settings)
        orchestrator = Orchestrator(context)
        return cls(
            settings=resolved_settings,
            logger=logger,
            context=context,
            orchestrator=orchestrator,
        )

    def startup(self) -> None:
        """Log the runtime startup sequence."""

        self.logger.info("Qwen3-Coder-Next Foundation Runtime Starting")
        self.logger.info("Repository Skeleton Loaded")

    def shutdown(self) -> None:
        """Log the runtime shutdown sequence and release logger handlers."""

        self.logger.info("Shutdown Complete")
        ApplicationLogger.shutdown(RUNTIME_LOGGER_NAME)
        ApplicationLogger.shutdown(BOOTSTRAP_LOGGER_NAME)
