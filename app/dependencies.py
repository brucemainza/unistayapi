"""FastAPI dependencies: database sessions and authentication."""

from collections.abc import AsyncGenerator
from typing import Annotated

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


# Convenience alias for endpoints that require an authenticated user.
CurrentUser = Annotated[User, Depends(get_current_user)]
