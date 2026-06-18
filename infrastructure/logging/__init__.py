"""Reusable structured logging.

A thin, dependency-light wrapper over ``structlog`` so every layer logs through
one consistent, configurable entry point. Console-friendly by default; emits
JSON when ``json_output`` is enabled (for aggregation in dev/prod).
"""

from __future__ import annotations

import logging
from typing import Any

import structlog

__all__ = ["configure_logging", "get_logger"]


def configure_logging(*, level: str = "INFO", json_output: bool = False) -> None:
    """Configure process-wide structured logging. Idempotent; call once on startup."""
    logging.basicConfig(format="%(message)s", level=level.upper())

    renderer: Any = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level.upper())
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structured logger. Pass ``__name__`` from the call site."""
    return structlog.get_logger(name)
