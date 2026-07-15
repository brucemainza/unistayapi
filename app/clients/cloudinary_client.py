"""Cloudinary image upload client."""

import asyncio

import cloudinary
import cloudinary.uploader

from app.config import settings
from app.exceptions import AppError
from app.logging_config import get_logger

logger = get_logger(__name__)

_SENSITIVE_KEYS = {
    "api_key",
    "api_secret",
    "authorization",
    "key",
    "secret",
    "signature",
    "token",
}


class CloudinaryError(AppError):
    def __init__(self, message: str = "Cloudinary upload failed"):
        super().__init__(message, 502)


def _configure() -> None:
    """Configure the Cloudinary SDK when all credentials are present."""
    if (
        settings.cloudinary_cloud_name
        and settings.cloudinary_api_key
        and settings.cloudinary_api_secret
    ):
        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            secure=settings.cloudinary_secure,
        )


_configure()


def _redact_sensitive(value):
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if any(sensitive in key_text for sensitive in _SENSITIVE_KEYS):
                redacted[key] = "<REDACTED>"
            else:
                redacted[key] = _redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    return value


def _extract_cloudinary_error(exc: Exception) -> dict:
    """Best-effort extraction of Cloudinary's error payload."""
    payload: dict = {"message": str(exc)}
    if hasattr(exc, "message"):
        payload["message"] = str(exc.message)
    if hasattr(exc, "http_code"):
        payload["http_code"] = exc.http_code
    if hasattr(exc, "code"):
        payload["code"] = exc.code
    if hasattr(exc, "status"):
        payload["status"] = exc.status
    if hasattr(exc, "response"):
        response = exc.response
        payload["response"] = response if isinstance(response, (dict, list, str, int, float, bool, type(None))) else str(response)
    if hasattr(exc, "error"):
        error = exc.error
        payload["error"] = error if isinstance(error, (dict, list, str, int, float, bool, type(None))) else str(error)
    return _redact_sensitive(payload)


async def upload_image(
    file_bytes: bytes, filename: str, folder: str | None = None
) -> str:
    """Upload image bytes to Cloudinary and return the HTTPS delivery URL."""
    if not settings.cloudinary_cloud_name:
        raise CloudinaryError("CLOUDINARY_CLOUD_NAME is not configured")
    if not settings.cloudinary_api_key:
        raise CloudinaryError("CLOUDINARY_API_KEY is not configured")
    if not settings.cloudinary_api_secret:
        raise CloudinaryError("CLOUDINARY_API_SECRET is not configured")

    try:
        result = await asyncio.to_thread(
            cloudinary.uploader.upload,
            file_bytes,
            folder=folder or settings.cloudinary_folder,
            resource_type="image",
        )
    except Exception as exc:
        error_payload = _extract_cloudinary_error(exc)
        logger.error(
            "Cloudinary upload failed",
            extra={
                "error_type": type(exc).__name__,
                "cloud_name": settings.cloudinary_cloud_name,
                "folder": folder or settings.cloudinary_folder,
                "error": error_payload,
            },
        )
        raise CloudinaryError() from exc

    url = result.get("secure_url") or result.get("url")
    if not url:
        raise CloudinaryError("Cloudinary response did not contain a URL")
    return url
