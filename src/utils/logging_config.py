"""
Centralized logging configuration for the research engine.

This module sets up structured logging with JSON formatting, file rotation,
and console output. It provides consistent logging across all components.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from pythonjsonlogger.json import JsonFormatter
from config.settings import Settings, get_settings
from typing import Any, Callable, Optional


class CustomJsonFormatter(JsonFormatter):
    """
    Custom JSON formatter with additional fields.

    Adds timestamp, logger name, and custom fields to all log records.
    """

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Add logger name
        log_record["logger"] = record.name

        # Add file and line number for debugging
        if record.levelno >= logging.DEBUG:
            log_record["file"] = record.pathname
            log_record["line"] = record.lineno

        # Add any extra fields passed via logger
        log_record.update(message_dict)


def setup_logging(settings: Settings | None = None) -> logging.Logger:
    """
    Configure logging for the application.

    Sets up both file and console handlers with appropriate formatters.
    Creates necessary directories if they don't exist.

    Args:
        settings: Settings instance. If None, uses cached global settings.

    Returns:
        logging.Logger: Root logger for the application

    Example:
        >>> logger = setup_logging()
        >>> logger.info("Application started")
    """
    if settings is None:
        settings = get_settings()

    # Ensure log directory exists
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create formatter based on settings
    if settings.log_format == "json":
        formatter = CustomJsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(name)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # File handler with rotation
    try:
        from logging.handlers import RotatingFileHandler

        file_handler = RotatingFileHandler(
            settings.log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, settings.log_level))
        root_logger.addHandler(file_handler)
    except Exception as e:
        # Fallback to basic file handler if rotation fails
        file_handler = logging.FileHandler(settings.log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, settings.log_level))
        root_logger.addHandler(file_handler)

    # Console handler
    if settings.log_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(getattr(logging, settings.log_level))
        root_logger.addHandler(console_handler)

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)

    # Create application logger
    app_logger = logging.getLogger("research_engine")
    app_logger.setLevel(getattr(logging, settings.log_level))

    app_logger.info(
        "Logging initialized",
        extra={
            "log_file": str(settings.log_file),
            "log_level": settings.log_level,
            "log_format": settings.log_format,
        },
    )

    return app_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    This is a convenience function to get child loggers under the
    application's logger hierarchy.

    Args:
        name: Logger name (e.g., "orchestrator", "chains.summarization")

    Returns:
        logging.Logger: Configured logger instance

    Example:
        >>> logger = get_logger("orchestrator")
        >>> logger.info("Processing query")
    """
    return logging.getLogger(f"research_engine.{name}")


class LogContext:
    """
    Context manager for adding extra fields to log records.

    Useful for adding request IDs, user IDs, or other contextual
    information to all logs within a scope.

    Example:
        >>> with LogContext(request_id="abc123", user="alice"):
        ...     logger.info("Processing request")
    """

    def __init__(self, **extra_fields):
        self.extra_fields = extra_fields
        self.old_factory: Optional[Callable[..., logging.LogRecord]] = None

    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()

        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            # Ensure old_factory exists before calling it to satisfy type checkers
            if self.old_factory is not None:
                record = self.old_factory(*args, **kwargs)
            else:
                record = logging.LogRecord(*args, **kwargs)  # fallback syntax

            # type: ignore[attr-defined]
            record.extra_fields = self.extra_fields
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.old_factory is not None:
            logging.setLogRecordFactory(self.old_factory)
