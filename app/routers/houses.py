"""Houses router: listing, search, detail, rooms, similar, nearby, ETA, and static map."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.google_maps_client import GoogleMapsClient
from app.dependencies import get_db
from app.repositories.eta_cache_repo import EtaCacheRepository
from app.repositories.house_repo import HouseRepository
from app.repositories.room_repo import RoomRepository
from app.repositories.university_repo import UniversityRepository
from app.schemas.common import envelope
from app.schemas.house import HouseSearchParams
from app.services.geo_service import GeoService
from app.services.house_service import HouseService

router = APIRouter()


def _geo_service(db: AsyncSession) -> GeoService:
    return GeoService(
        house_repo=HouseRepository(db),
        university_repo=UniversityRepository(db),
        eta_repo=EtaCacheRepository(db),
        maps_client=GoogleMapsClient(),
    )


@router.get("")
async def list_houses(
    params: HouseSearchParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Search and list houses with optional filters."""
    if params.university_id:
        result = await _geo_service(db).search_by_university(
            university_id=params.university_id,
            radius_m=params.radius_m,
            page=params.page,
            limit=params.limit,
            q=params.q,
            amenities=params.amenities,
            min_price=params.min_price,
            max_price=params.max_price,
        )
        return envelope(True, "Houses retrieved", result)

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


@router.get("/{house_id}/eta")
async def get_eta(
    house_id: str,
    university_id: str,
    mode: str = "DRIVE",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return cached or fresh ETA from a university to this house."""
    eta = await _geo_service(db).get_eta(house_id, university_id, mode)
    return envelope(True, "ETA retrieved", eta)


@router.get("/{house_id}/static-map")
async def static_map(
    house_id: str,
    zoom: int = 15,
    width: int = 400,
    height: int = 250,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return a signed Google Static Maps URL for the house location."""
    url = await _geo_service(db).build_static_map_url(
        house_id, zoom=zoom, width=width, height=height
    )
    return envelope(True, "Static map URL generated", {"url": url})
