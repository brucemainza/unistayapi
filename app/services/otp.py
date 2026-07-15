"""Email OTP lifecycle backed by Redis.

Codes are never stored in plain text; only SHA-256 hashes are written to Redis.
"""

import hashlib
import hmac
import secrets

import redis.asyncio as aioredis

from app.config import settings
from app.exceptions import RateLimitError


def _otp_key(email: str) -> str:
    return f"otp:{email.lower()}"


def _cooldown_key(email: str) -> str:
    return f"otp:cooldown:{email.lower()}"


def _attempts_key(email: str) -> str:
    return f"otp:attempts:{email.lower()}"


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


async def issue_otp(redis: aioredis.Redis, email: str) -> str:
    """Generate a 6-digit code, hash it, and store it in Redis with a cooldown.

    Raises ``RateLimitError`` if the resend cooldown for this email is active.
    """
    cooldown = _cooldown_key(email)
    if await redis.exists(cooldown):
        raise RateLimitError("Please wait before requesting another code")

    code = f"{secrets.randbelow(1_000_000):06d}"
    code_hash = _hash_code(code)

    pipe = redis.pipeline()
    pipe.set(_otp_key(email), code_hash, ex=settings.otp_ttl_seconds)
    pipe.set(cooldown, "1", ex=settings.otp_resend_cooldown)
    pipe.delete(_attempts_key(email))
    await pipe.execute()

    return code


async def verify_otp(redis: aioredis.Redis, email: str, submitted_code: str) -> bool:
    """Check a submitted code against the stored hash.

    Atomically increments the attempt counter and raises ``RateLimitError`` once
    ``OTP_MAX_ATTEMPTS`` is exceeded.  On success the OTP and attempt keys are
    deleted.  Returns ``False`` on a mismatch so the caller controls the error
    response.
    """
    attempts = _attempts_key(email)
    current_attempts = await redis.incr(attempts)
    if current_attempts == 1:
        await redis.expire(attempts, settings.otp_ttl_seconds)

    if current_attempts > settings.otp_max_attempts:
        raise RateLimitError("Too many attempts; please request a new code")

    stored_hash = await redis.get(_otp_key(email))
    if stored_hash is None:
        return False

    if not hmac.compare_digest(_hash_code(submitted_code), stored_hash):
        return False

    pipe = redis.pipeline()
    pipe.delete(_otp_key(email))
    pipe.delete(attempts)
    await pipe.execute()
    return True
