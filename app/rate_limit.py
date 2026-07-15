"""Redis-backed fixed-window rate limiting shared across routers."""

from fastapi import Request

from app.exceptions import RateLimitError

import redis.asyncio as aioredis

_MAX_DEFAULT = 30
_WINDOW_DEFAULT = 60


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


async def enforce_fixed_window(
    *,
    redis: aioredis.Redis,
    key_prefix: str,
    request: Request,
    max_requests: int = _MAX_DEFAULT,
    window_seconds: int = _WINDOW_DEFAULT,
    extra: str | None = None,
    message: str = "Rate limit exceeded",
) -> None:
    """Enforce a per-IP (optionally per-key) Redis fixed-window limit.

    Increments a counter keyed by ``{key_prefix}:{ip}[:{extra}]`` and raises
    ``RateLimitError`` once ``max_requests`` are exceeded within
    ``window_seconds``. Works across multiple Uvicorn workers because the
    state lives in Redis.
    """
    ip = _client_ip(request)
    key = f"{key_prefix}:{ip}"
    if extra is not None:
        key = f"{key}:{extra}"

    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, window_seconds)
    if current > max_requests:
        raise RateLimitError(message)
