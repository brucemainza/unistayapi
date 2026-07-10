"""Favorites router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_db
from app.repositories.favorite_repo import FavoriteRepository
from app.repositories.house_repo import HouseRepository
from app.schemas.common import envelope
from app.schemas.favorite import FavoriteCreateRequest
from app.services.favorite_service import FavoriteService

router = APIRouter()


def _service(db: AsyncSession) -> FavoriteService:
    return FavoriteService(FavoriteRepository(db), HouseRepository(db))


@router.get("")
async def list_favorites(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict:
    favorites = await _service(db).list_favorites(current_user.id)
    return envelope(True, "Favorites retrieved", favorites)


@router.post("")
async def add_favorite(
    body: FavoriteCreateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    house = await _service(db).add_favorite(current_user.id, body.house_id)
    return envelope(True, "Favorite added", house)


@router.delete("/{house_id}")
async def remove_favorite(
    house_id: str, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict:
    await _service(db).remove_favorite(current_user.id, house_id)
    return envelope(True, "Favorite removed", None)
