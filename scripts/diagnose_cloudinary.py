#!/usr/bin/env python3
"""Standalone Cloudinary credential/upload diagnostic.

Reads the app's Cloudinary env vars and attempts a minimal signed upload directly
via the Cloudinary SDK. Prints the full response or exception without routing
through the FastAPI app, so we can isolate credentials/config from app code bugs.
"""

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

from app.config import settings


def redact(value: str | None) -> str:
    if not value:
        return "<not set>"
    if len(value) <= 8:
        return "***"
    return value[:4] + "..." + value[-4:]


def main() -> None:
    print("Cloudinary configuration diagnostic")
    print("=" * 50)
    print(f"CLOUDINARY_CLOUD_NAME: {settings.cloudinary_cloud_name or '<not set>'}")
    print(f"CLOUDINARY_API_KEY: {redact(settings.cloudinary_api_key)}")
    print(f"CLOUDINARY_API_SECRET: {redact(settings.cloudinary_api_secret)}")
    print(f"CLOUDINARY_FOLDER: {settings.cloudinary_folder}")
    print()

    if not all(
        [
            settings.cloudinary_cloud_name,
            settings.cloudinary_api_key,
            settings.cloudinary_api_secret,
        ]
    ):
        print("ERROR: One or more Cloudinary credentials are missing.")
        sys.exit(1)

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=settings.cloudinary_secure,
    )

    # Try a minimal signed URL first to confirm signature generation
    print("1. Generating a signed URL sample...")
    try:
        url, signature_options = cloudinary_url(
            "sample.jpg",
            sign_url=True,
            type="authenticated",
        )
        print(f"   Signed URL generated OK: {url[:80]}...")
        print(f"   Signature options: {signature_options}")
    except Exception as exc:
        print(f"   Signed URL generation failed: {type(exc).__name__}: {exc}")

    # Try a minimal upload using a valid 1x1 PNG
    print("\n2. Attempting a minimal upload...")
    png_path = Path(__file__).parent / "test_image.png"
    image_bytes = png_path.read_bytes() if png_path.exists() else io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100).getvalue()
    try:
        result = cloudinary.uploader.upload(
            image_bytes,
            folder=settings.cloudinary_folder,
            resource_type="image",
        )
        print("   Upload succeeded!")
        print(f"   secure_url: {result.get('secure_url')}")
        print(f"   url: {result.get('url')}")
        print(f"   public_id: {result.get('public_id')}")
        print(f"   Full response keys: {list(result.keys())}")
    except Exception as exc:
        print(f"   Upload failed: {type(exc).__name__}")
        print(f"   str(exc): {exc}")
        if hasattr(exc, "message"):
            print(f"   exc.message: {exc.message}")
        if hasattr(exc, "http_code"):
            print(f"   exc.http_code: {exc.http_code}")
        if hasattr(exc, "code"):
            print(f"   exc.code: {exc.code}")
        if hasattr(exc, "json"):
            try:
                print(f"   exc.json(): {exc.json()}")
            except Exception:
                pass


if __name__ == "__main__":
    main()
