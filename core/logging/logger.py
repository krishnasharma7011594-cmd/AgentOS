"""
Structured Logging Configuration

Configures structlog to ensure consistent, machine-readable JSON logging across
all AgentOS layers. Shared by all components via standard structlog bindings.

Architecture Layer: Core / Logging
"""

import logging
import sys
from typing import Any, List

import structlog

from core.config.settings import settings


def setup_logger() -> structlog.stdlib.BoundLogger:
    """Initializes and configures the global structured logger."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    shared_processors: List[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.debug:
        shared_processors.append(structlog.dev.ConsoleRenderer())
    else:
        shared_processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()  # type: ignore[no-any-return]


logger = setup_logger()
