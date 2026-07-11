"""Transactional email delivery through Resend."""

import asyncio

import resend

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

# TODO: switch to a verified domain sender once UniStay's domain is verified.
_OTP_SENDER = "UniStay <onboarding@resend.dev>"


async def send_otp_email(email: str, code: str) -> None:
    """Send the OTP verification email in a background task.

    Failures are logged but never raised so the caller is not interrupted.
    """
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured; skipping OTP email")
        return

    resend.api_key = settings.resend_api_key

    try:
        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": _OTP_SENDER,
                "to": email,
                "subject": "Your UniStay verification code",
                "html": (
                    f"<p>Your UniStay verification code is <strong>{code}</strong>. "
                    f"It expires in {settings.otp_ttl_seconds // 60} minutes.</p>"
                ),
            },
        )
    except Exception as exc:
        logger.warning(
            "Failed to send OTP email",
            extra={"email": email, "error": type(exc).__name__},
        )
