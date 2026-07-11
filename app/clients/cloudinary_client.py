"""Cloudinary image upload client."""

import asyncio

import cloudinary
import cloudinary.uploader

from app.config import settings
from app.exceptions import AppError


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
        raise CloudinaryError(f"Cloudinary upload failed: {exc}") from exc

    url = result.get("secure_url") or result.get("url")
    if not url:
        raise CloudinaryError("Cloudinary response did not contain a URL")
    return url
