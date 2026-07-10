"""FastAPI dependencies: database sessions and authentication."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.exceptions import AuthError
from app.models import User

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


async def _get_or_create_dev_user(db: AsyncSession) -> User:
    """Return the development student user, creating it if necessary."""
    dev_email = "dev@unistay.local"
    dev_phone = "+233000000000"

    result = await db.execute(select(User).where(User.email == dev_email))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(
        full_name="Development Student",
        phone=dev_phone,
        email=dev_email,
        password_hash="dev-password-not-used",
        role="student",
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


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

    if settings.environment != "production" and token == "dev-student-token":
        return await _get_or_create_dev_user(db)

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
        )
    except JWTError as exc:
        raise AuthError("Invalid or expired token") from exc

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthError("Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthError("User not found")

    return user


# Convenience alias for endpoints that require an authenticated user.
CurrentUser = Annotated[User, Depends(get_current_user)]
