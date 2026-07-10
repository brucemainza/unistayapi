"""Structured JSON logging configuration and correlation-id helpers."""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)


class _JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        correlation_id = _correlation_id.get()
        if correlation_id:
            payload["correlation_id"] = correlation_id

        if hasattr(record, "extra"):
            payload.update(record.extra)

        # Never include exception tracebacks in production.
        if record.exc_info and not is_production():
            payload["exception"] = self.formatException(record.exc_info)
        elif record.exc_info:
            payload["exception"] = "exception suppressed in production"

        return json.dumps(payload, default=str)


def is_production() -> bool:
    """Return True when the running environment is production."""
    return get_environment() == "production"


def get_environment() -> str:
    """Read the ENVIRONMENT variable, defaulting to development."""
    import os

    return os.environ.get("ENVIRONMENT", "development").lower()


def get_correlation_id() -> str | None:
    """Return the correlation id for the current execution context."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: str | None) -> None:
    """Set the correlation id for the current execution context."""
    _correlation_id.set(correlation_id)


def generate_correlation_id() -> str:
    """Generate a new correlation id."""
    return str(uuid.uuid4())


def setup_logging(level: int | str = logging.INFO) -> None:
    """Configure the root logger for structured JSON output."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())

    root = logging.getLogger()
    root.handlers = []
    root.addHandler(handler)
    root.setLevel(level)

    # Reduce noise from third-party libraries in production.
    if is_production():
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured for the application."""
    return logging.getLogger(name)
