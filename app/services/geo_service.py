"""Geolocation business logic."""

from datetime import datetime, timedelta, timezone
from typing import Any

from app.clients.google_maps_client import GoogleMapsClient, GoogleMapsError
from app.exceptions import NotFoundError
from app.repositories.eta_cache_repo import EtaCacheRepository
from app.repositories.house_repo import HouseRepository
from app.repositories.university_repo import UniversityRepository
from app.services.serializers import house_to_dict


CACHE_TTL_DAYS = 30


class GeoService:
    def __init__(
        self,
        house_repo: HouseRepository | None,
        university_repo: UniversityRepository,
        eta_repo: EtaCacheRepository | None,
        maps_client: GoogleMapsClient,
    ) -> None:
        self.house_repo = house_repo
        self.university_repo = university_repo
        self.eta_repo = eta_repo
        self.maps_client = maps_client

    async def search_by_university(
        self,
        university_id: str,
        radius_m: int = 3000,
        page: int = 1,
        limit: int = 20,
        **filters: Any,
    ) -> dict:
        if self.house_repo is None:
            raise NotImplementedError("House repository is required for search")

        university = await self.university_repo.get_by_id(university_id)
        if university is None:
            raise NotFoundError("University not found")

        houses_with_dist, total = await self.house_repo.search_near_university(
            university_id=university_id,
            radius_m=radius_m,
            page=page,
            limit=limit,
            **filters,
        )
        return {
            "items": [
                house_to_dict(house, distance_m=dist_m)
                for house, dist_m in houses_with_dist
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
        }

    async def get_eta(
        self, house_id: str, university_id: str, mode: str = "DRIVE"
    ) -> dict:
        if self.house_repo is None or self.eta_repo is None:
            raise NotImplementedError("House and ETA repositories are required")

        house = await self.house_repo.get_by_id(house_id)
        if house is None:
            raise NotFoundError("House not found")
        university = await self.university_repo.get_by_id(university_id)
        if university is None:
            raise NotFoundError("University not found")

        mode = mode.upper()
        cached = await self.eta_repo.get(house_id, university_id, mode)
        if cached and self._is_fresh(cached.computed_at):
            return {
                "durationS": cached.duration_s,
                "distanceM": cached.distance_m,
                "mode": cached.mode,
                "cached": True,
            }

        from app.geo import parse_point

        house_lat, house_lon = parse_point(house.coords)
        campus_lat, campus_lon = parse_point(university.coords)
        if house_lat is None or campus_lat is None:
            raise NotFoundError("Coordinates missing")

        matrix = await self.maps_client.compute_route_matrix(
            origin={"latitude": campus_lat, "longitude": campus_lon},
            destination={"latitude": house_lat, "longitude": house_lon},
            mode=mode,
        )
        rows = matrix if isinstance(matrix, list) else matrix.get("rows", [])
        if not rows:
            raise GoogleMapsError("No route returned")

        first_row = rows[0]
        element = (
            first_row.get("elements", [{}])[0]
            if "elements" in first_row
            else first_row
        )
        duration_text = element.get("duration", "0s")
        duration_s = (
            int(duration_text.rstrip("s"))
            if isinstance(duration_text, str)
            else 0
        )
        distance_m = element.get("distanceMeters", 0)

        await self.eta_repo.upsert(
            house_id=house_id,
            university_id=university_id,
            mode=mode,
            duration_s=duration_s,
            distance_m=distance_m,
        )
        return {
            "durationS": duration_s,
            "distanceM": distance_m,
            "mode": mode,
            "cached": False,
        }

    def _is_fresh(self, computed_at: datetime) -> bool:
        now = datetime.now(timezone.utc)
        if computed_at.tzinfo is None:
            computed_at = computed_at.replace(tzinfo=timezone.utc)
        return now - computed_at < timedelta(days=CACHE_TTL_DAYS)

    async def autocomplete(self, input_text: str, session_token: str) -> dict:
        return await self.maps_client.autocomplete(
            input_text=input_text, session_token=session_token
        )

    async def place_details(self, place_id: str, session_token: str) -> dict:
        return await self.maps_client.place_details(
            place_id=place_id, session_token=session_token
        )

    async def get_static_map_image(
        self,
        house_id: str,
        zoom: int = 15,
        width: int = 400,
        height: int = 250,
    ) -> tuple[bytes, str]:
        if self.house_repo is None:
            raise NotImplementedError("House repository is required")

        house = await self.house_repo.get_by_id(house_id)
        if house is None:
            raise NotFoundError("House not found")

        from app.geo import parse_point

        lat, lon = parse_point(house.coords)
        if lat is None or lon is None:
            raise NotFoundError("House coordinates missing")
        return await self.maps_client.fetch_static_map(lat, lon, zoom, width, height)
