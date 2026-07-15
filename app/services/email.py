"""Transactional email delivery through Resend."""

import asyncio
import base64

import resend

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


def _resend_error_metadata(exc: Exception) -> dict[str, str | int | None]:
    """Return safe Resend diagnostics without including credentials or content."""
    return {
        "error": type(exc).__name__,
        "resend_error_type": getattr(exc, "error_type", None),
        "resend_code": getattr(exc, "code", None),
    }


async def send_otp_email(email: str, code: str) -> bool:
    """Send an OTP email directly through Resend and report delivery acceptance."""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured; skipping OTP email")
        return False

    resend.api_key = settings.resend_api_key

    try:
        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": settings.resend_from_email,
                "to": email,
                "subject": "Your UniStay verification code",
                "html": (
                    "<link href=\"https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap\" rel=\"stylesheet\">"
                    "<div style=\"font-family: 'Quicksand', Verdana, sans-serif; background-color: #f4f4f4; padding: 20px 0; width: 100%;\">"
                    "<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"max-width: 480px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden;\">"
                    "<tr><td style=\"background-color: #FF7A00; padding: 24px; text-align: center;\">"
                    "<h1 style=\"color: #ffffff; font-size: 24px; font-weight: 700; margin: 0; letter-spacing: 1px;\">UniStay</h1>"
                    "</td></tr>"
                    "<tr><td style=\"padding: 30px 20px; text-align: center;\">"
                    "<h2 style=\"color: #333; font-weight: 600; margin-bottom: 10px; font-size: 20px;\">Verification Code</h2>"
                    "<p style=\"color: #555; font-size: 15px; margin-bottom: 25px;\">Use the code below to verify your account:</p>"
                    f"<div style=\"display: inline-block; background-color: #fff5eb; "
                    "border: 2px solid #FF7A00; border-radius: 12px; padding: 18px 30px; "
                    f"font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #FF7A00; max-width: 90%;\">{code}</div>"
                    f"<p style=\"color: #888; font-size: 13px; margin-top: 25px;\">"
                    f"This code expires in {settings.otp_ttl_seconds // 60} minutes.</p>"
                    "</td></tr>"
                    "<tr><td style=\"background-color: #fafafa; padding: 15px; text-align: center;\">"
                ),
            },
        )
        return True
    except Exception as exc:
        logger.warning(
            "Failed to send OTP email",
            extra={"email": email, **_resend_error_metadata(exc)},
        )
        return False


async def send_booking_receipt_email(
    email: str, *, pdf_bytes: bytes, filename: str
) -> bool:
    """Send a printable booking receipt PDF to the student."""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured; skipping receipt email")
        return False

    resend.api_key = settings.resend_api_key
    attachment = {
        "filename": filename,
        "content": base64.b64encode(pdf_bytes).decode("ascii"),
        "content_type": "application/pdf",
    }

    try:
        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": settings.resend_from_email,
                "to": email,
                "subject": "Your UniStay booking receipt",
                "html": (
                    "<p>Your UniStay booking receipt is attached as a PDF.</p>"
                    "<p>You can download or print it for your records.</p>"
                ),
                "attachments": [attachment],
            },
        )
        return True
    except Exception as exc:
        logger.warning(
            "Failed to send booking receipt email",
            extra={"email": email, **_resend_error_metadata(exc)},
        )
        return False
