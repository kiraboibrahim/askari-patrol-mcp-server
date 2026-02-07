"""
Centralized logging configuration for Askari Patrol.

This module provides a unified logging setup with support for console and file
handlers, structured formatting, and environment-based configuration.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path


def setup_logging(
    log_level: str | None = None,
    log_file: str | None = None,
    log_format: str = "standard",
    enable_file_logging: bool = True,
) -> None:
    """
    Configure application-wide logging with console and optional file handlers.

    This function sets up a comprehensive logging configuration with:
    - Console output with colored formatting (if supported)
    - Optional rotating file handler for persistent logs
    - Structured formatting with timestamps and module information
    - Environment-based configuration via LOG_LEVEL, LOG_FILE, and LOG_FORMAT

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            Defaults to LOG_LEVEL environment variable or INFO.
        log_file: Path to log file. Defaults to LOG_FILE environment variable
            or 'logs/askari_patrol.log'.
        log_format: Format style ('standard' or 'json'). Defaults to LOG_FORMAT
            environment variable or 'standard'.
        enable_file_logging: Whether to enable file logging. Defaults to True.

    Example:
        >>> setup_logging(log_level="DEBUG", log_file="logs/debug.log")
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("Application started")
    """
    # Resolve configuration from environment or defaults
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO").upper()
    log_file = log_file or os.getenv("LOG_FILE", "logs/askari_patrol.log")
    log_format = log_format or os.getenv("LOG_FORMAT", "standard").lower()

    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Define log formats
    if log_format == "json":
        # Structured JSON format for production/parsing
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(name)s", "message": "%(message)s"}',
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation
    if enable_file_logging:
        try:
            # Ensure log directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Rotating file handler (10MB max, keep 5 backups)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

            root_logger.info(f"File logging enabled: {log_file}")
        except Exception as e:
            root_logger.warning(f"Failed to set up file logging: {e}")

    root_logger.info(f"Logging configured: level={log_level}, format={log_format}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified module.

    This is a convenience wrapper around logging.getLogger() that ensures
    consistent logger naming across the application.

    Args:
        name: The name of the logger, typically __name__ from the calling module.

    Returns:
        A configured logger instance.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.debug("Debug message")
    """
    return logging.getLogger(name)
