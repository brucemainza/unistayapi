"""Users router for profile and account endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_db
from app.repositories.user_repo import UserRepository
from app.schemas.common import envelope
from app.schemas.user import UserUpdateRequest
from app.services.user_service import UserService

router = APIRouter()


@router.get("/me")
async def get_me(current_user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
    """Return the currently authenticated user's profile."""
    service = UserService(UserRepository(db))
    user = await service.get_profile(current_user.id)
    return envelope(True, "User profile", user)


@router.patch("/me")
async def update_me(
    body: UserUpdateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update the currently authenticated user's profile."""
    service = UserService(UserRepository(db))
    user = await service.update_profile(current_user.id, body)
    return envelope(True, "Profile updated", user)


@router.get("/me/stats")
async def get_stats(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict:
    """Return activity statistics for the current user."""
    service = UserService(UserRepository(db))
    stats = await service.get_stats(current_user.id)
    return envelope(True, "User stats", stats)


@router.get("/me/accommodation")
async def get_accommodation(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict:
    """Return the current user's booking/accommodation information."""
    service = UserService(UserRepository(db))
    accommodation = await service.get_accommodation(current_user.id)
    return envelope(True, "User accommodation", accommodation)
