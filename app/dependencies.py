"""FastAPI dependencies: database sessions, Redis, and authentication."""

from collections.abc import AsyncGenerator
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.exceptions import AuthError
from app.models import User
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService

security = HTTPBearer(auto_error=False)

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
)
async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

_redis_pool: aioredis.Redis | None = None


def _get_redis_pool() -> aioredis.Redis:
    """Return the shared async Redis connection pool, creating it on demand."""
    global _redis_pool
    if _redis_pool is None:
        if not settings.redis_url:
            raise RuntimeError("REDIS_URL is not configured")
        _redis_pool = aioredis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=30,
            socket_timeout=30,
            health_check_interval=30,
        )
    return _redis_pool


async def close_redis() -> None:
    """Close the shared Redis pool, if it was opened."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None


async def ping_redis() -> bool:
    """Return whether the configured Redis connection responds to PING."""
    client = _get_redis_pool()
    return bool(await client.ping())


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """Yield the shared async Redis client for a single request."""
    client = _get_redis_pool()
    try:
        yield client
    finally:
        pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session for a single request."""
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate the bearer token and return the authenticated user.

    In non-production environments the token ``dev-student-token`` is
    accepted and resolves to a development student user (created on first
    use). Otherwise the token is validated as a JWT signed with
    ``settings.jwt_secret``.
    """
    if credentials is None or not credentials.credentials:
        raise AuthError()

    token = credentials.credentials
    repo = UserRepository(db)

    if settings.environment != "production" and token == "dev-student-token":
        return await repo.get_dev_user()

    payload = AuthService.verify_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise AuthError("Invalid token payload")

    user = await repo.get_by_id(user_id)
    if user is None:
        raise AuthError("User not found")

    return user


async def require_landlord(current_user: User = Depends(get_current_user)) -> User:
    """Require the authenticated user to be a landlord."""
    if current_user.role != "landlord":
        raise AuthError("Landlord access required")
    return current_user


async def require_student(current_user: User = Depends(get_current_user)) -> User:
    """Require the authenticated user to be a student."""
    if current_user.role != "student":
        raise AuthError("Student access required")
    return current_user


# Convenience alias for endpoints that require an authenticated user.
CurrentUser = Annotated[User, Depends(get_current_user)]
LandlordUser = Annotated[User, Depends(require_landlord)]
StudentUser = Annotated[User, Depends(require_student)]
