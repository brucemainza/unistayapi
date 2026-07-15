"""Users router for profile and account endpoints."""

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser
from app.providers import get_user_service
from app.schemas.common import Envelope, envelope
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services.user_service import UserService

router = APIRouter()


@router.get("/me", response_model=Envelope[UserResponse])
async def get_me(
    current_user: CurrentUser,
    service: UserService = Depends(get_user_service),
) -> dict:
    """Return the currently authenticated user's profile."""
    user = await service.get_profile(current_user.id)
    return envelope(True, "User profile", user)


@router.patch("/me", response_model=Envelope[UserResponse])
async def update_me(
    body: UserUpdateRequest,
    current_user: CurrentUser,
    service: UserService = Depends(get_user_service),
) -> dict:
    """Update the currently authenticated user's profile."""
    user = await service.update_profile(current_user.id, body)
    return envelope(True, "Profile updated", user)


@router.get("/me/stats")
async def get_stats(
    current_user: CurrentUser,
    service: UserService = Depends(get_user_service),
) -> dict:
    """Return activity statistics for the current user."""
    stats = await service.get_stats(current_user.id)
    return envelope(True, "User stats", stats)


@router.get("/me/accommodation")
async def get_accommodation(
    current_user: CurrentUser,
    service: UserService = Depends(get_user_service),
) -> dict:
    """Return the current user's booking/accommodation information."""
    accommodation = await service.get_accommodation(current_user.id)
    return envelope(True, "User accommodation", accommodation)
