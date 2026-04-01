"""
Structured logging configuration for AudioAnalyzer.

Provides:
- JSON-formatted logs for production
- Colorized console output for development
- Context-aware logging with processing metadata
- File rotation and external log aggregation support

Usage:
------
>>> from utils.logging_setup import get_logger
>>> logger = get_logger("audio.processor")
>>> logger.info("processing_started", file_count=10, method="fwht")
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

try:
    import structlog
    from structlog.types import Processor
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False

# Default log format
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Union[str, Path]] = None,
    json_format: bool = False,
    include_context: bool = True,
) -> None:
    """Configure application-wide logging.
    
    Parameters
    ----------
    level : str
        Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_file : Optional[Union[str, Path]]
        Path to log file. If None, logs only to console.
    json_format : bool
        If True, use JSON format for structured logging.
    include_context : bool
        If True, include context information in logs.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    if HAS_STRUCTLOG:
        _setup_structlog(log_level, log_file, json_format, include_context)
    else:
        _setup_standard_logging(log_level, log_file)


def _setup_structlog(
    level: int,
    log_file: Optional[Union[str, Path]],
    json_format: bool,
    include_context: bool,
) -> None:
    """Set up structlog with processors."""
    import structlog
    from structlog.dev import ConsoleRenderer
    from structlog.processors import JSONRenderer
    
    # Shared processors for all loggers
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    if include_context:
        shared_processors.append(
            structlog.processors.UnicodeDecoder()
        )
    
    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging handlers
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if json_format:
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=shared_processors,
        )
    else:
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=True),
            foreign_pre_chain=shared_processors,
        )
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=shared_processors,
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add new handlers
    for handler in handlers:
        root_logger.addHandler(handler)


def _setup_standard_logging(
    level: int,
    log_file: Optional[Union[str, Path]],
) -> None:
    """Set up standard Python logging as fallback."""
    import logging.config
    
    handlers = ["console"]
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": DEFAULT_FORMAT,
                "datefmt": DEFAULT_DATE_FORMAT,
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
                "datefmt": DEFAULT_DATE_FORMAT,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "standard",
                "level": level,
            },
        },
        "loggers": {
            "": {
                "handlers": handlers,
                "level": level,
                "propagate": True,
            },
            "audio": {
                "handlers": handlers,
                "level": level,
                "propagate": False,
            },
            "processing": {
                "handlers": handlers,
                "level": level,
                "propagate": False,
            },
            "ui_new": {
                "handlers": handlers,
                "level": level,
                "propagate": False,
            },
        },
    }
    
    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(file_path),
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "detailed",
            "encoding": "utf-8",
        }
        handlers.append("file")
    
    logging.config.dictConfig(config)


def get_logger(name: str) -> "BoundLogger":
    """Get a logger instance with the given name.
    
    Parameters
    ----------
    name : str
        Logger name (typically module name)
    
    Returns
    -------
    BoundLogger
        A structlog or standard logger instance
    """
    if HAS_STRUCTLOG:
        return structlog.get_logger(name)
    else:
        return logging.getLogger(name)


class LogContext:
    """Context manager for adding temporary logging context.
    
    Example:
    -------
    >>> with LogContext(file="test.wav", method="fwht"):
    ...     logger.info("processing_started")
    """
    
    def __init__(self, **kwargs: Any):
        """Initialize context with key-value pairs."""
        self.context = kwargs
        self._token: Optional[Any] = None
    
    def __enter__(self) -> "LogContext":
        """Enter context and bind variables."""
        if HAS_STRUCTLOG:
            import structlog
            self._token = structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, *args: Any) -> None:
        """Exit context and unbind variables."""
        if HAS_STRUCTLOG and self._token is not None:
            import structlog
            structlog.contextvars.unbind_contextvars(*self.context.keys())


def log_performance(
    operation: str,
    duration_ms: float,
    **kwargs: Any,
) -> None:
    """Log a performance metric.
    
    Parameters
    ----------
    operation : str
        Name of the operation
    duration_ms : float
        Duration in milliseconds
    **kwargs : Any
        Additional context
    """
    logger = get_logger("performance")
    logger.info(
        operation,
        duration_ms=duration_ms,
        **kwargs,
    )


def log_error_with_context(
    error: Exception,
    operation: str,
    **kwargs: Any,
) -> None:
    """Log an error with additional context.
    
    Parameters
    ----------
    error : Exception
        The exception that occurred
    operation : str
        Name of the operation that failed
    **kwargs : Any
        Additional context
    """
    logger = get_logger("errors")
    logger.error(
        f"{operation}_failed",
        error_type=type(error).__name__,
        error_message=str(error),
        **kwargs,
    )


# Initialize default logging on import
_default_initialized = False


def ensure_logging_initialized() -> None:
    """Ensure logging is initialized with defaults."""
    global _default_initialized
    if not _default_initialized:
        setup_logging(level="INFO")
        _default_initialized = True


# Export public API
__all__ = [
    "setup_logging",
    "get_logger",
    "LogContext",
    "log_performance",
    "log_error_with_context",
    "ensure_logging_initialized",
    "HAS_STRUCTLOG",
]
