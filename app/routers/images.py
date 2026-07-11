"""Image upload endpoints backed by Cloudinary."""

from fastapi import APIRouter, Depends, File, UploadFile

from app.clients import cloudinary_client
from app.dependencies import CurrentUser
from app.exceptions import ValidationError
from app.schemas.common import envelope

router = APIRouter()

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
_MAX_SIZE = 5 * 1024 * 1024


def _validate_image(content: bytes, content_type: str | None, filename: str) -> None:
    """Validate image size and MIME type before uploading to Cloudinary."""
    if content_type not in _ALLOWED_TYPES:
        raise ValidationError("Only JPEG, PNG, and WebP images are allowed")
    if len(content) > _MAX_SIZE:
        raise ValidationError("Image must be smaller than 5MB")


@router.post("/upload")
async def upload_image(
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> dict:
    """Upload a single image to Cloudinary and return its delivery URL."""
    content = await file.read()
    _validate_image(content, file.content_type, file.filename or "image")

    url = await cloudinary_client.upload_image(
        content, file.filename or "image.jpg"
    )
    return envelope(True, "Image uploaded", {"url": url})


@router.post("/upload-multiple")
async def upload_multiple_images(
    current_user: CurrentUser,
    files: list[UploadFile] = File(...),
) -> dict:
    """Upload multiple images to Cloudinary and return their delivery URLs."""
    urls: list[str] = []
    for image_file in files:
        content = await image_file.read()
        _validate_image(
            content, image_file.content_type, image_file.filename or "image"
        )
        url = await cloudinary_client.upload_image(
            content, image_file.filename or "image.jpg"
        )
        urls.append(url)

    return envelope(True, "Images uploaded", {"urls": urls})
