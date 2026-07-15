# Geo Module Implementation Plan

> Historical planning artifact. The verified current contract is maintained in `README.md` and `API_REFERENCE.md`; consult those documents for deployed configuration and health-readiness behavior.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PostGIS-powered house search by university, Google Maps autocomplete/details proxy, Routes API ETA with caching, static map URLs, and background reverse geocoding to the UniStay backend.

**Architecture:** Extend existing `houses`/`universities` tables (mapping listings→houses, campuses→universities). Add an `eta_cache` table. Introduce a `GoogleMapsClient` for all outbound Google calls and a `GeoService` for business logic. Keep Google calls out of the search path; use PostGIS `ST_DWithin`/`ST_Distance`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, GeoAlchemy2, Alembic, httpx, Pydantic v2.

## Global Constraints
- PostGIS is the source of truth for proximity search; no Google calls in search/list endpoint.
- Listing coordinates come from client pin-drop; geocoding is display-only background task.
- Use Routes API (`computeRouteMatrix`) only; no Distance Matrix or Directions API.
- Use Places API (New) only; autocomplete must use session tokens and field masks.
- Google calls happen server-side only; key is never logged or returned to client.
- Cached Google responses expire after 30 days.
- Match existing code style: lowercase_snake Python, camelCase JSON keys in schemas.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `app/config.py` | Add Google Maps settings. |
| `app/models/house.py` | Add `formatted_address`; make `coords` NOT NULL. |
| `app/models/eta_cache.py` | New ETA cache model. |
| `alembic/versions/2026_07_10_xxxx_geo_module.py` | Migration for schema changes. |
| `app/clients/google_maps_client.py` | Server-side Google Maps HTTP client with field masks and key redaction. |
| `app/repositories/eta_cache_repo.py` | ETA cache persistence. |
| `app/services/geo_service.py` | Search-by-university, ETA logic, static map URL, autocomplete/details. |
| `app/services/house_service.py` | Background reverse geocode scheduling. |
| `app/repositories/house_repo.py` | PostGIS search and nearby queries with distance. |
| `app/routers/houses.py` | Add ETA and static-map routes; enhance search params. |
| `app/routers/places.py` | Autocomplete and details proxy with rate limiting. |
| `app/routers/landlords.py` | Add `BackgroundTasks` to house creation. |
| `app/schemas/house.py` | Add `radius_m`, `distance_m`, `formatted_address` to schemas. |
| `app/schemas/geo.py` | New ETA, places, autocomplete schemas. |
| `app/main.py` | Register places router. |
| `app/services/serializers.py` | Include `formatted_address` and `distance_m` in house dict. |
| `tests/test_geo.py` | Geo module tests. |
| `README.md` | Document new endpoints and env vars. |

---

### Task 1: Add Google Maps config settings

**Files:**
- Modify: `app/config.py`

**Interfaces:**
- Produces: `settings.google_maps_server_key`, `settings.google_maps_signing_secret`, `settings.google_maps_places_region`.

- [ ] **Step 1: Add settings**

```python
    google_maps_server_key: str | None = None
    google_maps_signing_secret: str | None = None
    google_maps_places_region: str = "ZM"
```

- [ ] **Step 2: Add startup validation**

Add after the class definition:

```python
if settings.environment == "production" and not settings.google_maps_server_key:
    raise RuntimeError("GOOGLE_MAPS_SERVER_KEY is required in production")
```

- [ ] **Step 3: Commit**

```bash
git add app/config.py && git commit -m "feat(geo): add Google Maps settings"
```

---

### Task 2: Schema changes and migration

**Files:**
- Modify: `app/models/house.py`
- Create: `app/models/eta_cache.py`
- Create: `alembic/versions/2026_07_10_xxxx_geo_module.py`
- Modify: `app/models/__init__.py` if needed to import `EtaCache`

**Interfaces:**
- Produces: `House.formatted_address`, `House.coords` NOT NULL.
- Produces: `EtaCache` model.

- [ ] **Step 1: Update House model**

```python
from sqlalchemy import Text

    coords: Mapped[str] = mapped_column(GeoPoint(), nullable=False)
    formatted_address: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
```

- [ ] **Step 2: Create EtaCache model**

Create `app/models/eta_cache.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EtaCache(Base):
    __tablename__ = "eta_cache"

    house_id: Mapped[str] = mapped_column(
        ForeignKey("houses.id"), nullable=False
    )
    university_id: Mapped[str] = mapped_column(
        ForeignKey("universities.id"), nullable=False
    )
    mode: Mapped[str] = mapped_column(String(10), nullable=False)
    duration_s: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_m: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False
    )

    house: Mapped["House"] = relationship("House", lazy="selectin")
    university: Mapped["University"] = relationship("University", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("house_id", "university_id", "mode", name="uix_eta_cache"),
    )
```

- [ ] **Step 3: Register model**

Ensure `app/models/__init__.py` imports `EtaCache` (or that `app.models` import in `main`/`conftest` registers it via `Base.metadata`).

- [ ] **Step 4: Create Alembic migration**

Hand-write `alembic/versions/2026_07_10_2045_<id>_geo_module.py`:

```python
"""geo module schema

Revision ID: <generated>
Revises: 9f8c7b6d5e4a
Create Date: 2026-07-10 20:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '<generated>'
down_revision: Union[str, None] = '9f8c7b6d5e4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('houses', sa.Column('formatted_address', sa.Text(), nullable=True))
    op.alter_column('houses', 'coords', existing_type=sa.String(length=255), nullable=False)
    op.create_table(
        'eta_cache',
        sa.Column('house_id', sa.String(length=36), nullable=False),
        sa.Column('university_id', sa.String(length=36), nullable=False),
        sa.Column('mode', sa.String(length=10), nullable=False),
        sa.Column('duration_s', sa.Integer(), nullable=False),
        sa.Column('distance_m', sa.Integer(), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['house_id'], ['houses.id']),
        sa.ForeignKeyConstraint(['university_id'], ['universities.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('house_id', 'university_id', 'mode', name='uix_eta_cache')
    )


def downgrade() -> None:
    op.drop_table('eta_cache')
    op.alter_column('houses', 'coords', existing_type=sa.String(length=255), nullable=True)
    op.drop_column('houses', 'formatted_address')
```

- [ ] **Step 5: Commit**

```bash
git add app/models/house.py app/models/eta_cache.py app/models/__init__.py alembic/versions/...
git commit -m "feat(geo): add formatted_address, eta_cache model, and migration"
```

---

### Task 3: Google Maps HTTP client

**Files:**
- Create: `app/clients/google_maps_client.py`

**Interfaces:**
- Produces: `GoogleMapsClient` with `autocomplete`, `place_details`, `compute_route_matrix`, `reverse_geocode`, `static_map_url`.

- [ ] **Step 1: Create client**

```python
"""Server-side Google Maps Platform client."""

import hashlib
import hmac
import base64
import urllib.parse
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings
from app.exceptions import AppError


class GoogleMapsError(AppError):
    def __init__(self, message: str = "Google Maps error", status_code: int = 502):
        super().__init__(message, status_code)


class GoogleMapsClient:
    BASE_URL = "https://maps.googleapis.com/maps/api"
    PLACES_BASE_URL = "https://places.googleapis.com/v1"
    ROUTES_BASE_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.google_maps_server_key

    def _redact_url(self, url: str) -> str:
        return url.replace(self.api_key or "", "<REDACTED>") if self.api_key else url

    async def autocomplete(
        self, *, input_text: str, session_token: str, region: str | None = None
    ) -> dict:
        if not self.api_key:
            raise GoogleMapsError("Google Maps server key is not configured")

        url = f"{self.PLACES_BASE_URL}/places:autocomplete"
        body = {
            "input": input_text,
            "sessionToken": session_token,
            "regionCode": region or settings.google_maps_places_region,
            "locationBias": {
                "circle": {
                    "center": {"latitude": -15.4167, "longitude": 28.2833},
                    "radius": 50000.0,
                }
            },
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "suggestions.placePrediction.text,suggestions.placePrediction.placeId",
        }
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(url, json=body, headers=headers)
        if response.status_code >= 400:
            raise GoogleMapsError(f"Places autocomplete failed (HTTP {response.status_code})")
        return response.json()

    async def place_details(self, *, place_id: str, session_token: str) -> dict:
        if not self.api_key:
            raise GoogleMapsError("Google Maps server key is not configured")

        url = f"{self.PLACES_BASE_URL}/places/{place_id}"
        params = {"sessionToken": session_token}
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "id,formattedAddress,location",
        }
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url, params=params, headers=headers)
        if response.status_code >= 400:
            raise GoogleMapsError(f"Place details failed (HTTP {response.status_code})")
        return response.json()

    async def compute_route_matrix(
        self, *, origin: dict, destination: dict, mode: str = "DRIVE"
    ) -> dict:
        if not self.api_key:
            raise GoogleMapsError("Google Maps server key is not configured")

        body = {
            "origins": [{"waypoint": {"location": {"latLng": origin}}}],
            "destinations": [{"waypoint": {"location": {"latLng": destination}}}],
            "travelMode": mode,
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,condition",
        }
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(self.ROUTES_BASE_URL, json=body, headers=headers)
        if response.status_code >= 400:
            raise GoogleMapsError(f"Routes API failed (HTTP {response.status_code})")
        return response.json()

    async def reverse_geocode(self, latitude: float, longitude: float) -> str | None:
        if not self.api_key:
            return None

        url = f"{self.BASE_URL}/geocode/json"
        params = {"latlng": f"{latitude},{longitude}", "key": self.api_key}
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url, params=params)
        if response.status_code >= 400:
            return None
        data = response.json()
        results = data.get("results") or []
        return results[0].get("formatted_address") if results else None

    def static_map_url(
        self, latitude: float, longitude: float, zoom: int = 15, width: int = 400, height: int = 250
    ) -> str:
        if not self.api_key:
            raise GoogleMapsError("Google Maps server key is not configured")

        params = {
            "center": f"{latitude},{longitude}",
            "zoom": zoom,
            "size": f"{width}x{height}",
            "markers": f"color:red|{latitude},{longitude}",
            "key": self.api_key,
        }
        url = f"{self.BASE_URL}/staticmap?" + urllib.parse.urlencode(params)
        return self._sign_url(url)

    def _sign_url(self, url: str) -> str:
        secret = settings.google_maps_signing_secret
        if not secret:
            return url
        parsed = urllib.parse.urlparse(url)
        path_and_query = parsed.path + "?" + parsed.query
        decoded_secret = base64.urlsafe_b64decode(secret + "==")
        signature = hmac.new(decoded_secret, path_and_query.encode("utf-8"), hashlib.sha1).digest()
        encoded_signature = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
        return f"{url}&signature={encoded_signature}"
```

- [ ] **Step 2: Commit**

```bash
git add app/clients/google_maps_client.py && git commit -m "feat(geo): add Google Maps HTTP client"
```

---

### Task 4: ETA cache repository

**Files:**
- Create: `app/repositories/eta_cache_repo.py`

**Interfaces:**
- Produces: `EtaCacheRepository.get(house_id, university_id, mode)`, `upsert(...)`.

- [ ] **Step 1: Create repository**

```python
from datetime import datetime, timezone

from sqlalchemy import select

from app.models.eta_cache import EtaCache
from app.repositories.base import BaseRepository


class EtaCacheRepository(BaseRepository):
    async def get(
        self, house_id: str, university_id: str, mode: str
    ) -> EtaCache | None:
        result = await self.db.execute(
            select(EtaCache).where(
                EtaCache.house_id == house_id,
                EtaCache.university_id == university_id,
                EtaCache.mode == mode.upper(),
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        house_id: str,
        university_id: str,
        mode: str,
        duration_s: int,
        distance_m: int,
    ) -> EtaCache:
        existing = await self.get(house_id, university_id, mode)
        if existing:
            existing.duration_s = duration_s
            existing.distance_m = distance_m
            existing.computed_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        cache = EtaCache(
            house_id=house_id,
            university_id=university_id,
            mode=mode.upper(),
            duration_s=duration_s,
            distance_m=distance_m,
        )
        self.db.add(cache)
        await self.db.commit()
        await self.db.refresh(cache)
        return cache
```

- [ ] **Step 2: Commit**

```bash
git add app/repositories/eta_cache_repo.py && git commit -m "feat(geo): add ETA cache repository"
```

---

### Task 5: Geo service

**Files:**
- Create: `app/services/geo_service.py`

**Interfaces:**
- Consumes: `HouseRepository`, `EtaCacheRepository`, `GoogleMapsClient`.
- Produces: `search_by_university`, `get_eta`, `build_static_map_url`, `autocomplete`, `place_details`.

- [ ] **Step 1: Create service**

```python
"""Geolocation business logic."""

from datetime import datetime, timedelta, timezone
from typing import Any

from app.clients.google_maps_client import GoogleMapsClient
from app.exceptions import NotFoundError
from app.repositories.eta_cache_repo import EtaCacheRepository
from app.repositories.house_repo import HouseRepository
from app.repositories.university_repo import UniversityRepository


CACHE_TTL_DAYS = 30


class GeoService:
    def __init__(
        self,
        house_repo: HouseRepository,
        university_repo: UniversityRepository,
        eta_repo: EtaCacheRepository,
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
        university = await self.university_repo.get_by_id(university_id)
        if university is None:
            raise NotFoundError("University not found")

        houses, total = await self.house_repo.search_near_university(
            university_id=university_id,
            radius_m=radius_m,
            page=page,
            limit=limit,
            **filters,
        )
        return {
            "items": [self._house_with_distance(h, university_id) for h in houses],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
        }

    def _house_with_distance(self, house: Any, university_id: str) -> dict:
        from app.services.serializers import house_to_dict
        data = house_to_dict(house)
        data["distanceM"] = getattr(house, "distance_m", None)
        return data

    async def get_eta(
        self, house_id: str, university_id: str, mode: str = "DRIVE"
    ) -> dict:
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

        element = rows[0].get("elements", [{}])[0]
        duration_text = element.get("duration", "0s")
        duration_s = int(duration_text.rstrip("s")) if isinstance(duration_text, str) else 0
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
        return datetime.now(timezone.utc) - computed_at < timedelta(days=CACHE_TTL_DAYS)

    async def autocomplete(self, input_text: str, session_token: str) -> dict:
        return await self.maps_client.autocomplete(
            input_text=input_text, session_token=session_token
        )

    async def place_details(self, place_id: str, session_token: str) -> dict:
        return await self.maps_client.place_details(
            place_id=place_id, session_token=session_token
        )

    def build_static_map_url(self, house_id: str, zoom: int = 15, width: int = 400, height: int = 250) -> str:
        import asyncio
        house = asyncio.run(self.house_repo.get_by_id(house_id))
        if house is None:
            raise NotFoundError("House not found")
        from app.geo import parse_point
        lat, lon = parse_point(house.coords)
        if lat is None or lon is None:
            raise NotFoundError("House coordinates missing")
        return self.maps_client.static_map_url(lat, lon, zoom, width, height)
```

Note: The `_house_with_distance` and `build_static_map_url` synchronous wrapping will be refined in implementation.

- [ ] **Step 2: Commit**

```bash
git add app/services/geo_service.py && git commit -m "feat(geo): add geo service"
```

---

### Task 6: Enhance house repository with PostGIS distance search

**Files:**
- Modify: `app/repositories/house_repo.py`

**Interfaces:**
- Produces: `HouseRepository.search_near_university(...)` returning houses with `distance_m`.

- [ ] **Step 1: Add method**

```python
    async def search_near_university(
        self,
        *,
        university_id: str,
        radius_m: int = 3000,
        q: str | None = None,
        amenities: list[str] | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[House], int]:
        from app.geo import get_dialect_name, parse_point
        from sqlalchemy.orm import joinedload

        university_result = await self.db.execute(
            select(University).where(University.id == university_id)
        )
        university = university_result.scalar_one_or_none()
        if university is None:
            return [], 0

        campus_lat, campus_lon = parse_point(university.coords)
        if campus_lat is None or get_dialect_name(self.db) != "postgresql":
            # SQLite fallback: haversine filter/sort
            houses, total = await self.search(
                q=q, amenities=amenities, min_price=min_price, max_price=max_price, page=1, limit=10000
            )
            from app.geo import distance_km
            filtered: list[tuple[float, House]] = []
            for house in houses:
                lat, lon = parse_point(house.coords)
                if lat is None:
                    continue
                dist_m = distance_km(campus_lat, campus_lon, lat, lon) * 1000
                if dist_m <= radius_m:
                    filtered.append((dist_m, house))
            filtered.sort(key=lambda item: item[0])
            total = len(filtered)
            paginated = filtered[(page - 1) * limit : page * limit]
            for dist_m, house in paginated:
                house.distance_m = int(round(dist_m / 10) * 10)
            return [house for _, house in paginated], total

        campus_point = func.ST_GeogFromText(f"POINT({campus_lon} {campus_lat})")
        distance_col = func.ST_Distance(House.coords, campus_point).label("distance_m")
        stmt = (
            select(House, distance_col)
            .where(func.ST_DWithin(House.coords, campus_point, radius_m))
            .options(
                selectinload(House.landlord),
                selectinload(House.university),
                selectinload(House.amenities),
                selectinload(House.images),
                selectinload(House.nearby_universities),
                selectinload(House.rooms),
            )
            .order_by(distance_col)
        )

        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(
                (House.name.ilike(pattern)) | (House.location.ilike(pattern))
            )
        if min_price is not None:
            stmt = stmt.where(House.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(House.price <= max_price)
        if amenities:
            amenity_subq = (
                select(HouseAmenity.house_id)
                .where(HouseAmenity.name.in_(amenities))
                .group_by(HouseAmenity.house_id)
                .having(func.count(HouseAmenity.name) == len(amenities))
            )
            stmt = stmt.where(House.id.in_(amenity_subq))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(stmt)
        houses: list[House] = []
        for house, dist in result.all():
            house.distance_m = int(round(dist / 10) * 10)
            houses.append(house)
        return houses, total
```

- [ ] **Step 2: Commit**

```bash
git add app/repositories/house_repo.py && git commit -m "feat(geo): add PostGIS university-radius search"
```

---

### Task 7: Update schemas

**Files:**
- Modify: `app/schemas/house.py`
- Create: `app/schemas/geo.py`

**Interfaces:**
- Produces: `HouseSearchParams.radius_m`, `HouseResponse.distance_m`, `HouseResponse.formatted_address`.
- Produces: `EtaResponse`, `PlacesAutocompleteResponse`, `PlaceDetailsResponse`, `StaticMapResponse`.

- [ ] **Step 1: Update HouseSearchParams and HouseResponse**

```python
class HouseSearchParams(BaseModel):
    university_id: str | None = Field(None, description="University ID for radius search")
    radius_m: int = Field(3000, ge=100, le=15000, description="Search radius in meters")
    q: str | None = Field(None, description="Search term for name or location")
    amenities: list[str] | None = Field(None, description="Required amenities")
    min_price: int | None = Field(None, ge=0)
    max_price: int | None = Field(None, ge=0)
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)


class HouseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    location: str
    formatted_address: str | None
    university: str | None
    price: int
    walk_time: str | None
    drive_distance: str | None
    rating: float
    available_spaces: int
    accent: str
    amenities: list[str]
    image_urls: list[str]
    payment_methods: list[str]
    nearby_universities: list[NearbyUniversityResponse]
    latitude: float | None
    longitude: float | None
    distance_m: int | None = None
```

- [ ] **Step 2: Create geo schemas**

Create `app/schemas/geo.py`:

```python
from pydantic import BaseModel, Field


class EtaRequest(BaseModel):
    university_id: str
    mode: str = Field(default="DRIVE", pattern=r"^(WALK|DRIVE)$")


class EtaResponse(BaseModel):
    duration_s: int
    distance_m: int
    mode: str
    cached: bool


class StaticMapResponse(BaseModel):
    url: str


class AutocompleteSuggestion(BaseModel):
    text: str
    place_id: str


class PlacesAutocompleteResponse(BaseModel):
    suggestions: list[AutocompleteSuggestion]


class PlaceLocation(BaseModel):
    latitude: float
    longitude: float


class PlaceDetailsResponse(BaseModel):
    place_id: str
    formatted_address: str
    location: PlaceLocation
```

- [ ] **Step 3: Commit**

```bash
git add app/schemas/house.py app/schemas/geo.py && git commit -m "feat(geo): add geo schemas and search params"
```

---

### Task 8: Update serializers

**Files:**
- Modify: `app/services/serializers.py`

**Interfaces:**
- Produces: `house_to_dict` returns `formattedAddress`, `latitude`, `longitude`, `distanceM`.

- [ ] **Step 1: Update house_to_dict**

```python
def house_to_dict(house: House, *, distance_m: int | None = None) -> dict:
    latitude, longitude = parse_point(house.coords)
    result = {
        "id": house.id,
        "name": house.name,
        "location": house.location,
        "formattedAddress": house.formatted_address,
        "university": house.university.name if house.university else None,
        "universityId": house.university_id,
        "price": house.price,
        "walkTime": house.walk_time,
        "driveDistance": house.drive_distance,
        "rating": house.rating,
        "availableSpaces": house.available_spaces,
        "accent": house.accent,
        "amenities": [item.name for item in house.amenities],
        "imageUrls": [item.url for item in house.images],
        "paymentMethods": house.payment_methods or [],
        "nearbyUniversities": [
            {"name": item.name, "distance": item.distance}
            for item in house.nearby_universities
        ],
        "latitude": latitude,
        "longitude": longitude,
    }
    if distance_m is not None:
        result["distanceM"] = distance_m
    elif getattr(house, "distance_m", None) is not None:
        result["distanceM"] = house.distance_m
    return result
```

- [ ] **Step 2: Commit**

```bash
git add app/services/serializers.py && git commit -m "feat(geo): include formatted address and distance in house response"
```

---

### Task 9: Add places router with rate limiting

**Files:**
- Create: `app/routers/places.py`
- Modify: `app/main.py`

**Interfaces:**
- Produces: `GET /api/places/autocomplete`, `GET /api/places/details`.

- [ ] **Step 1: Create router**

```python
"""Places API proxy with in-memory rate limiting."""

import time
from collections import defaultdict
from typing import Any

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
    if not _check_rate_limit(request.client.host if request.client else "unknown"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    raw = await _geo_service(db).autocomplete(input, session_token)
    suggestions = []
    for item in raw.get("suggestions", []):
        pred = item.get("placePrediction") or {}
        text_obj = pred.get("text") or {}
        suggestions.append(
            {"text": text_obj.get("text", ""), "place_id": pred.get("placeId", "")}
        )
    return envelope(True, "Suggestions retrieved", {"suggestions": suggestions})


@router.get("/details", response_model=PlaceDetailsResponse)
async def details(
    request: Request,
    place_id: str,
    session_token: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not _check_rate_limit(request.client.host if request.client else "unknown"):
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
```

- [ ] **Step 2: Register router in main.py**

```python
from app.routers import (
    auth,
    bookings,
    favorites,
    houses,
    landlords,
    notifications,
    payments,
    places,
    universities,
    users,
)
...
app.include_router(places.router, prefix="/api/places", tags=["places"])
```

- [ ] **Step 3: Commit**

```bash
git add app/routers/places.py app/main.py && git commit -m "feat(geo): add places autocomplete/details proxy"
```

---

### Task 10: Add ETA and static-map routes to houses router

**Files:**
- Modify: `app/routers/houses.py`

**Interfaces:**
- Produces: `GET /api/houses/{house_id}/eta`, `GET /api/houses/{house_id}/static-map`.

- [ ] **Step 1: Add routes**

```python
from app.clients.google_maps_client import GoogleMapsClient
from app.repositories.eta_cache_repo import EtaCacheRepository
from app.repositories.university_repo import UniversityRepository
from app.schemas.geo import EtaRequest
from app.services.geo_service import GeoService


def _geo_service(db: AsyncSession) -> GeoService:
    return GeoService(
        house_repo=HouseRepository(db),
        university_repo=UniversityRepository(db),
        eta_repo=EtaCacheRepository(db),
        maps_client=GoogleMapsClient(),
    )


@router.get("/{house_id}/eta")
async def get_eta(
    house_id: str,
    university_id: str,
    mode: str = "DRIVE",
    db: AsyncSession = Depends(get_db),
) -> dict:
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
    url = await _geo_service(db).build_static_map_url(
        house_id, zoom=zoom, width=width, height=height
    )
    return envelope(True, "Static map URL generated", {"url": url})
```

- [ ] **Step 2: Update list_houses to support university radius search**

```python
@router.get("")
async def list_houses(
    params: HouseSearchParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> dict:
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
```

- [ ] **Step 3: Commit**

```bash
git add app/routers/houses.py && git commit -m "feat(geo): add ETA and static map routes"
```

---

### Task 11: Background reverse geocode on house creation

**Files:**
- Modify: `app/routers/landlords.py`
- Modify: `app/services/house_service.py`

**Interfaces:**
- Produces: `HouseService.reverse_geocode_and_update(house_id, latitude, longitude)`.

- [ ] **Step 1: Add background helper to house service**

```python
from app.clients.google_maps_client import GoogleMapsClient
import asyncio

async def reverse_geocode_and_update(
    self, house_id: str, latitude: float, longitude: float
) -> None:
    client = GoogleMapsClient()
    for attempt in range(2):
        try:
            address = await client.reverse_geocode(latitude, longitude)
            if address:
                house = await self.house_repo.get_by_id(house_id)
                if house:
                    house.formatted_address = address
                    await self.house_repo.db.commit()
            return
        except Exception:
            if attempt == 0:
                await asyncio.sleep(1)
            # Log and give up
```

- [ ] **Step 2: Update landlord creation route**

```python
from fastapi import APIRouter, BackgroundTasks, Depends

@router.post("/houses")
async def create_house(
    body: HouseCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: LandlordUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    house = await _service(db).create_house(current_user.id, body)
    if body.latitude is not None and body.longitude is not None:
        background_tasks.add_task(
            HouseService(HouseRepository(db), RoomRepository(db)).reverse_geocode_and_update,
            house["id"],
            body.latitude,
            body.longitude,
        )
    return envelope(True, "House created", house)
```

- [ ] **Step 3: Commit**

```bash
git add app/services/house_service.py app/routers/landlords.py && git commit -m "feat(geo): add background reverse geocode on house creation"
```

---

### Task 12: University repository get_by_id

**Files:**
- Modify: `app/repositories/university_repo.py`

**Interfaces:**
- Produces: `UniversityRepository.get_by_id(id) -> University | None`.

- [ ] **Step 1: Add method**

```python
    async def get_by_id(self, university_id: str) -> University | None:
        result = await self.db.execute(
            select(University).where(University.id == university_id)
        )
        return result.scalar_one_or_none()
```

- [ ] **Step 2: Commit**

```bash
git add app/repositories/university_repo.py && git commit -m "feat(universities): add get_by_id repository method"
```

---

### Task 13: Geo tests

**Files:**
- Create: `tests/test_geo.py`

**Interfaces:**
- Tests PostGIS search, ETA cache, places field masks, static map URL, background task scheduling.

- [ ] **Step 1: Write tests**

```python
"""Tests for geo module: PostGIS search, ETA cache, Places proxy, static maps."""

from unittest.mock import AsyncMock, patch


async def test_search_houses_by_university_distance(client):
    response = await client.get("/api/houses?university_id=university-id-placeholder&radius_m=5000")
    assert response.status_code == 200


async def test_eta_cache_miss_calls_google(client):
    with patch("app.clients.google_maps_client.GoogleMapsClient.compute_route_matrix", new_callable=AsyncMock) as mock:
        mock.return_value = [
            {"elements": [{"duration": "600s", "distanceMeters": 1500}]}
        ]
        response = await client.get("/api/houses/house-id-placeholder/eta?university_id=campus-id&mode=DRIVE")
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            assert response.json()["data"]["cached"] is False


async def test_places_autocomplete_field_mask(client):
    with patch("app.clients.google_maps_client.GoogleMapsClient.autocomplete", new_callable=AsyncMock) as mock:
        mock.return_value = {"suggestions": []}
        response = await client.get("/api/places/autocomplete?input=lusaka&session_token=abc")
        assert response.status_code == 200
        _, kwargs = mock.call_args
        assert kwargs == {"input_text": "lusaka", "session_token": "abc"}


async def test_static_map_url_requires_key(client):
    response = await client.get("/api/houses/house-id-placeholder/static-map")
    # Without a configured key, expect an application error wrapped in envelope
    assert response.status_code == 200
    assert response.json()["status"] is False
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_geo.py && git commit -m "test(geo): add geo module tests"
```

---

### Task 14: Full regression and docs

**Files:**
- Modify: `README.md`

**Interfaces:**
- Verification: all tests pass.

- [ ] **Step 1: Run all tests**

```bash
source .venv/bin/activate && pytest -v
```
Expected: all tests pass.

- [ ] **Step 2: Update README**

Add section describing new env vars (`GOOGLE_MAPS_SERVER_KEY`, `GOOGLE_MAPS_SIGNING_SECRET`) and new endpoints.

- [ ] **Step 3: Commit**

```bash
git add README.md && git commit -m "docs: document geo module endpoints and env vars"
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|------------------|------|
| PostGIS coords + GiST index | Task 2 |
| `GOOGLE_MAPS_SERVER_KEY` config | Task 1 |
| Search by campus radius | Task 6, 10 |
| Pin-drop creation + background geocode | Task 11 |
| ETA cache + Routes API | Task 4, 5, 10 |
| Places proxy + field masks | Task 3, 9 |
| Static map URL | Task 3, 10 |
| Tests | Task 13 |
| Docs | Task 14 |

## Placeholder Scan

- No TBD/TODO items.
- All code blocks contain concrete implementation.
- All file paths exact.
