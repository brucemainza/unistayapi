"""Shared Pydantic helpers and response envelope utilities."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


def envelope(status: bool, message: str, data: Any | None = None) -> dict[str, Any]:
    """Return a Flutter-compatible JSON envelope."""
    return {"status": status, "message": message, "data": data}


class Envelope(BaseModel, Generic[T]):
    """Pydantic envelope model that mirrors the Flutter response shape.

    Wire endpoints with ``response_model=Envelope[ConcreteResponse]`` so the
    OpenAPI schema documents the actual response type (instead of a generic
    dict) and frontend clients can be code-generated from ``/openapi.json``.
    """

    status: bool
    message: str
    data: T | None = None
