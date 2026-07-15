"""Houses router: listing, search, detail, rooms, similar, nearby, ETA, and static map."""

from fastapi import APIRouter, Depends, Response

from app.providers import get_geo_service, get_house_service
from app.schemas.common import envelope
from app.schemas.house import HouseSearchParams
from app.services.geo_service import GeoService
from app.services.house_service import HouseService

router = APIRouter()


@router.get("")
async def list_houses(
    params: HouseSearchParams = Depends(),
    house_service: HouseService = Depends(get_house_service),
    geo_service: GeoService = Depends(get_geo_service),
) -> dict:
    """Search and list houses with optional filters."""
    if params.university_id:
        result = await geo_service.search_by_university(
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

    houses = await house_service.list_houses(
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
    house_service: HouseService = Depends(get_house_service),
) -> dict:
    """Return houses near the given coordinate."""
    houses = await house_service.get_nearby(latitude, longitude, radius_km)
    return envelope(True, "Nearby houses retrieved", houses)


@router.get("/{house_id}")
async def get_house(
    house_id: str,
    house_service: HouseService = Depends(get_house_service),
) -> dict:
    """Return detailed information for a single house."""
    house = await house_service.get_house(house_id)
    return envelope(True, "House retrieved", house)


@router.get("/{house_id}/rooms")
async def list_rooms(
    house_id: str,
    house_service: HouseService = Depends(get_house_service),
) -> dict:
    """Return all rooms for a house."""
    rooms = await house_service.list_rooms(house_id)
    return envelope(True, "Rooms retrieved", rooms)


@router.get("/{house_id}/similar")
async def similar_houses(
    house_id: str,
    house_service: HouseService = Depends(get_house_service),
) -> dict:
    """Return houses similar to the given house."""
    houses = await house_service.get_similar(house_id)
    return envelope(True, "Similar houses retrieved", houses)


@router.get("/{house_id}/eta")
async def get_eta(
    house_id: str,
    university_id: str,
    mode: str = "DRIVE",
    geo_service: GeoService = Depends(get_geo_service),
) -> dict:
    """Return cached or fresh ETA from a university to this house."""
    eta = await geo_service.get_eta(house_id, university_id, mode)
    return envelope(True, "ETA retrieved", eta)


@router.get("/{house_id}/static-map")
async def static_map(
    house_id: str,
    zoom: int = 15,
    width: int = 400,
    height: int = 250,
    geo_service: GeoService = Depends(get_geo_service),
) -> Response:
    """Proxy a Google Static Maps image without exposing the server key."""
    image, content_type = await geo_service.get_static_map_image(
        house_id, zoom=zoom, width=width, height=height
    )
    return Response(content=image, media_type=content_type)
