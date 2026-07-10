"""Shared Pydantic helpers and response envelope utilities."""

from typing import Any


def envelope(status: bool, message: str, data: Any | None = None) -> dict[str, Any]:
    """Return a Flutter-compatible JSON envelope."""
    return {"status": status, "message": message, "data": data}
