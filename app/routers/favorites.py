"""Favorites router."""

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser
from app.providers import get_favorite_service
from app.schemas.common import Envelope, envelope
from app.schemas.favorite import FavoriteCreateRequest
from app.services.favorite_service import FavoriteService

router = APIRouter()


@router.get("", response_model=Envelope[list[dict]])
async def list_favorites(
    current_user: CurrentUser,
    service: FavoriteService = Depends(get_favorite_service),
) -> dict:
    favorites = await service.list_favorites(current_user.id)
    return envelope(True, "Favorites retrieved", favorites)


@router.post("", response_model=Envelope[dict])
async def add_favorite(
    body: FavoriteCreateRequest,
    current_user: CurrentUser,
    service: FavoriteService = Depends(get_favorite_service),
) -> dict:
    house = await service.add_favorite(current_user.id, body.house_id)
    return envelope(True, "Favorite added", house)


@router.delete("/{house_id}", response_model=Envelope[None])
async def remove_favorite(
    house_id: str,
    current_user: CurrentUser,
    service: FavoriteService = Depends(get_favorite_service),
) -> dict:
    await service.remove_favorite(current_user.id, house_id)
    return envelope(True, "Favorite removed", None)
