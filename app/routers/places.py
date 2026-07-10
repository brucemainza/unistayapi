"""Places API proxy with in-memory rate limiting."""

import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.google_maps_client import GoogleMapsClient
from app.dependencies import get_db
from app.repositories.university_repo import UniversityRepository
from app.schemas.common import envelope
from app.schemas.geo import PlaceDetailsResponse, PlacesAutocompleteResponse
from app.services.geo_service import GeoService

router = APIRouter()

_RATE_LIMIT_MAX = 30
_RATE_LIMIT_WINDOW = 60
_limiter: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    window = [t for t in _limiter[client_ip] if now - t < _RATE_LIMIT_WINDOW]
    _limiter[client_ip] = window
    if len(window) >= _RATE_LIMIT_MAX:
        return False
    window.append(now)
    return True


def _geo_service(db: AsyncSession) -> GeoService:
    return GeoService(
        house_repo=None,
        university_repo=UniversityRepository(db),
        eta_repo=None,
        maps_client=GoogleMapsClient(),
    )


@router.get("/autocomplete", response_model=PlacesAutocompleteResponse)
async def autocomplete(
    request: Request,
    input: str,
    session_token: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    raw = await _geo_service(db).autocomplete(input, session_token)
    suggestions = []
    for item in raw.get("suggestions", []):
        pred = item.get("placePrediction") or {}
        text_obj = pred.get("text") or {}
        suggestions.append(
            {
                "text": text_obj.get("text", ""),
                "place_id": pred.get("placeId", ""),
            }
        )
    return envelope(True, "Suggestions retrieved", {"suggestions": suggestions})


@router.get("/details", response_model=PlaceDetailsResponse)
async def details(
    request: Request,
    place_id: str,
    session_token: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    raw = await _geo_service(db).place_details(place_id, session_token)
    location = raw.get("location", {})
    data = {
        "place_id": raw.get("id", ""),
        "formatted_address": raw.get("formattedAddress", ""),
        "location": {
            "latitude": location.get("latitude", 0.0),
            "longitude": location.get("longitude", 0.0),
        },
    }
    return envelope(True, "Place details retrieved", data)
