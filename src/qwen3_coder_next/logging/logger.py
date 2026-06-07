"""Public logger access helpers."""

import logging

from qwen3_coder_next.config import AppSettings, get_settings
from qwen3_coder_next.logging.setup import (
    DEFAULT_LOGGER_NAME,
    setup_logging,
    teardown_logging,
)


class ApplicationLogger:
    """Central entry point for creating and retrieving application loggers."""

    @staticmethod
    def initialize(
        settings: AppSettings | None = None,
        *,
        logger_name: str = DEFAULT_LOGGER_NAME,
        level: int | None = None,
    ) -> logging.Logger:
        """Initialize the application logger from settings."""

        resolved_settings = settings or get_settings()
        return setup_logging(
            resolved_settings,
            logger_name=logger_name,
            level=level,
        )

    @staticmethod
    def get(name: str = DEFAULT_LOGGER_NAME) -> logging.Logger:
        """Return a named logger instance."""

        return logging.getLogger(name)

    @staticmethod
    def shutdown(name: str = DEFAULT_LOGGER_NAME) -> None:
        """Close and detach handlers for a named logger."""

        teardown_logging(logging.getLogger(name))


def get_logger(name: str = DEFAULT_LOGGER_NAME) -> logging.Logger:
    """Return a named logger instance."""

    return ApplicationLogger.get(name)
