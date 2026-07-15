"""Structured JSON logging configuration and correlation-id helpers."""

from __future__ import annotations

import contextvars
import json
import logging
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)
_runtime_environment: str | None = None
_SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "signature",
    "key",
    "cvv",
    "card_number",
)
_QUERY_SECRET_PATTERN = re.compile(
    r"(?i)(\b(?:api[_-]?key|key|authorization|password|secret|token|signature|cvv)\s*[=:]\s*)([^&,\s]+)"
)


def _redact_sensitive(value: Any, key: str | None = None) -> Any:
    """Redact credential-like fields before they reach structured logs."""
    if key and any(part in key.lower() for part in _SENSITIVE_KEY_PARTS):
        return "<REDACTED>"
    if isinstance(value, dict):
        return {str(item_key): _redact_sensitive(item, str(item_key)) for item_key, item in value.items()}
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_sensitive(item) for item in value)
    if isinstance(value, str):
        return _QUERY_SECRET_PATTERN.sub(r"\1<REDACTED>", value)
    return value


class _JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    _standard_record_keys = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }

    def _collect_extra(self, record: logging.LogRecord) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            payload.update(record.extra)

        for key, value in record.__dict__.items():
            if key not in self._standard_record_keys:
                payload[key] = value
        return payload

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

        payload.update(self._collect_extra(record))

        # Never include exception tracebacks in production.
        if record.exc_info and not is_production():
            payload["exception"] = self.formatException(record.exc_info)
        elif record.exc_info:
            payload["exception"] = "exception suppressed in production"

        return json.dumps(_redact_sensitive(payload), default=str)


def is_production() -> bool:
    """Return True when the running environment is production."""
    return get_environment() == "production"


def get_environment() -> str:
    """Read the ENVIRONMENT variable, defaulting to development."""
    import os

    if _runtime_environment:
        return _runtime_environment
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


def setup_logging(
    level: int | str = logging.INFO, environment: str | None = None
) -> None:
    """Configure the root logger for structured JSON output."""
    global _runtime_environment
    if environment:
        _runtime_environment = environment.lower()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())

    root = logging.getLogger()
    root.handlers = []
    root.addHandler(handler)
    root.setLevel(level)

    # Reduce noise from third-party libraries in production.
    if is_production():
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured for the application."""
    return logging.getLogger(name)
