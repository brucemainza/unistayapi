"""Places API proxy with Redis-backed rate limiting."""

from fastapi import APIRouter, Depends, Request

import redis.asyncio as aioredis

from app.dependencies import get_redis
from app.providers import get_places_geo_service
from app.rate_limit import enforce_fixed_window
from app.schemas.common import envelope
from app.services.geo_service import GeoService

router = APIRouter()

_RATE_LIMIT_MAX = 30
_RATE_LIMIT_WINDOW = 60


@router.get("/autocomplete")
async def autocomplete(
    request: Request,
    input: str,
    session_token: str,
    redis: aioredis.Redis = Depends(get_redis),
    geo_service: GeoService = Depends(get_places_geo_service),
) -> dict:
    await enforce_fixed_window(
        redis=redis,
        key_prefix="rate_limit:places",
        request=request,
        max_requests=_RATE_LIMIT_MAX,
        window_seconds=_RATE_LIMIT_WINDOW,
        message="Rate limit exceeded",
    )

    raw = await geo_service.autocomplete(input, session_token)
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


@router.get("/details")
async def details(
    request: Request,
    place_id: str,
    session_token: str,
    redis: aioredis.Redis = Depends(get_redis),
    geo_service: GeoService = Depends(get_places_geo_service),
) -> dict:
    await enforce_fixed_window(
        redis=redis,
        key_prefix="rate_limit:places",
        request=request,
        max_requests=_RATE_LIMIT_MAX,
        window_seconds=_RATE_LIMIT_WINDOW,
        message="Rate limit exceeded",
    )

    raw = await geo_service.place_details(place_id, session_token)
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
