"""Logging utilities for telemetry processing pipeline."""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


def setup_logger(
    name: str,
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: str = "logs",
) -> logging.Logger:
    """Setup logger with console and optional file output.

    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file name (will be placed in log_dir)
        log_dir: Directory for log files

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path / log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get existing logger or create a basic one.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        # Setup basic console logging if not configured
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


class PipelineLogger:
    """Context manager for pipeline stage logging with timing."""

    def __init__(self, logger: logging.Logger, stage_name: str):
        """Initialize pipeline logger.

        Args:
            logger: Logger instance
            stage_name: Name of pipeline stage
        """
        self.logger = logger
        self.stage_name = stage_name
        self.start_time: Optional[datetime] = None

    def __enter__(self):
        """Start stage logging."""
        self.start_time = datetime.now()
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Starting: {self.stage_name}")
        self.logger.info(f"{'='*60}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End stage logging with timing."""
        if exc_type is not None:
            self.logger.error(
                f"Stage '{self.stage_name}' FAILED with {exc_type.__name__}: {exc_val}"
            )
            return False

        duration = (datetime.now() - self.start_time).total_seconds()
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Completed: {self.stage_name} in {duration:.2f}s")
        self.logger.info(f"{'='*60}")
        return True
