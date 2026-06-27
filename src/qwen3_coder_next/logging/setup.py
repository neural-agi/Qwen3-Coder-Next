"""Logger setup utilities."""

import os
import logging
import tempfile
from pathlib import Path

from qwen3_coder_next.config import AppSettings
from qwen3_coder_next.logging.formatter import build_formatter


DEFAULT_LOGGER_NAME = "qwen3_coder_next"
DEFAULT_LOG_FILENAME = "application.log"


def resolve_log_level(settings: AppSettings, level: int | None = None) -> int:
    """Resolve the effective log level for the application."""

    if level is not None:
        return level
    if settings.debug:
        return logging.DEBUG
    return logging.INFO


def build_log_file_path(settings: AppSettings, filename: str = DEFAULT_LOG_FILENAME) -> Path:
    """Build the default log file path within the configured logs directory."""

    return settings.logs_dir / filename


def setup_logging(
    settings: AppSettings,
    *,
    logger_name: str = DEFAULT_LOGGER_NAME,
    level: int | None = None,
    log_filename: str = DEFAULT_LOG_FILENAME,
    reset_handlers: bool = True,
) -> logging.Logger:
    """Configure and return an application logger."""

    logger = logging.getLogger(logger_name)
    logger.setLevel(resolve_log_level(settings, level))
    logger.propagate = False

    if reset_handlers:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()

    formatter = build_formatter()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logger.level)
    console_handler.setFormatter(formatter)

    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = build_log_file_path(settings, log_filename)
    try:
        file_handler = logging.FileHandler(
            log_file_path,
            encoding="utf-8",
        )
    except PermissionError:
        fallback_dir = Path(tempfile.gettempdir()) / "qwen3-coder-next-logs"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        fallback_name = f"{Path(log_filename).stem}-{os.getpid()}{Path(log_filename).suffix}"
        file_handler = logging.FileHandler(
            fallback_dir / fallback_name,
            encoding="utf-8",
        )
    file_handler.setLevel(logger.level)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


def teardown_logging(logger: logging.Logger) -> None:
    """Detach and close all handlers for a logger."""

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
