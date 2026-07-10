"""Houses router: listing, search, detail, rooms, similar, and nearby."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.repositories.house_repo import HouseRepository
from app.repositories.room_repo import RoomRepository
from app.schemas.common import envelope
from app.schemas.house import HouseSearchParams
from app.services.house_service import HouseService

router = APIRouter()


@router.get("")
async def list_houses(
    params: HouseSearchParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Search and list houses with optional filters."""
    service = HouseService(HouseRepository(db), RoomRepository(db))
    houses = await service.list_houses(
        university=params.university,
        q=params.q,
        amenities=params.amenities,
        min_price=params.min_price,
        max_price=params.max_price,
        page=params.page,
        limit=params.limit,
    )
    return envelope(True, "Houses retrieved", houses)


@router.get("/nearby")
async def nearby_houses(
    latitude: float,
    longitude: float,
    radius_km: float = 10,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return houses near the given coordinate."""
    service = HouseService(HouseRepository(db), RoomRepository(db))
    houses = await service.get_nearby(latitude, longitude, radius_km)
    return envelope(True, "Nearby houses retrieved", houses)


@router.get("/{house_id}")
async def get_house(house_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Return detailed information for a single house."""
    service = HouseService(HouseRepository(db), RoomRepository(db))
    house = await service.get_house(house_id)
    return envelope(True, "House retrieved", house)


@router.get("/{house_id}/rooms")
async def list_rooms(house_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Return all rooms for a house."""
    service = HouseService(HouseRepository(db), RoomRepository(db))
    rooms = await service.list_rooms(house_id)
    return envelope(True, "Rooms retrieved", rooms)


@router.get("/{house_id}/similar")
async def similar_houses(house_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Return houses similar to the given house."""
    service = HouseService(HouseRepository(db), RoomRepository(db))
    houses = await service.get_similar(house_id)
    return envelope(True, "Similar houses retrieved", houses)
