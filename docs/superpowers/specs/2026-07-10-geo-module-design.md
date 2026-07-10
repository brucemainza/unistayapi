# Geo Module Design

## Goal
Add production-grade geolocation capabilities to the UniStay backend: PostGIS-powered house search by campus/university, Google Maps autocomplete/details proxy, Routes API ETA with caching, and static map thumbnail URLs.

## Context mapping
The existing codebase uses `houses` for listings and `universities` for campuses. This design adapts the prompt's terminology to those existing tables rather than creating duplicate `listings`/`campuses` tables.

## Non-negotiable decisions (from prompt)
1. PostGIS is the source of truth for proximity search; no Google calls in search path.
2. Listing coordinates come from the client's pin-drop (`latitude`/`longitude`); geocoding is display-only background task.
3. Google Routes API (`computeRouteMatrix`) only — no Distance Matrix or Directions legacy APIs.
4. Places API (New) only — autocomplete uses session tokens; every request uses field masks.
5. Google calls happen server-side only with a server-restricted key; key is never logged or returned.
6. Cached Google responses expire after 30 days max.

## Database changes

### `houses` table
- Migration makes `coords` `NOT NULL` (seed data already provides coordinates).
- Add `formatted_address` nullable text column for the background reverse-geocode result.
- Existing GiST spatial index on `coords` is kept.

### `universities` table
- Already has `coords` and a GiST index; no schema change required.
- Used as the "campus" reference data.

### New `eta_cache` table
- `id` (PK)
- `house_id` (FK)
- `university_id` (FK)
- `mode` (`WALK` | `DRIVE`)
- `duration_s` (int)
- `distance_m` (int)
- `computed_at` (timestamp)
- Unique index on `(house_id, university_id, mode)`.

## Config
- Add `GOOGLE_MAPS_SERVER_KEY` setting. In production, raise a clear startup error if missing.
- Add optional `GOOGLE_MAPS_SIGNING_SECRET` for signed Static Maps URLs.
- Add `GOOGLE_MAPS_PLACES_REGION` defaulting to `ZM`.
- Key is redacted from any exception/logs.

## Endpoints

### Enhanced house search
`GET /api/houses?university_id=<uuid>&radius_m=3000&...existing_filters...`
- When `university_id` is provided, filter with `ST_DWithin` against that university's `location`.
- Sort by `ST_Distance`.
- Return `distance_m` per house.
- No outbound HTTP call.

### ETA
`GET /api/houses/{house_id}/eta?university_id=<uuid>&mode=WALK|DRIVE`
- Check `eta_cache`; return cached row if < 30 days old.
- Otherwise call Google Routes API `computeRouteMatrix` (1×1).
- Upsert cache row and return `{duration_s, distance_m, mode, cached: false}`.

### Places proxy
`GET /api/places/autocomplete?input=<text>&session_token=<token>`
- Proxy to Places API (New) `:autocomplete`.
- Field mask: `suggestions.placePrediction.text,suggestions.placePrediction.placeId`.
- Region `ZM`; location bias circle centered on Zambia.

`GET /api/places/details?place_id=<id>&session_token=<token>`
- Proxy to Place Details.
- Field mask: `id,formattedAddress,location`.

### Static map helper
`GET /api/houses/{house_id}/static-map?zoom=15&width=400&height=250`
- Return a signed Static Maps URL for the house location.

### Listing creation
`POST /api/landlords/houses` (existing endpoint)
- Accepts required `latitude`/`longitude` (already supported).
- Enqueue `BackgroundTasks` to reverse-geocode and populate `formatted_address`.

## Background reverse geocode
- Uses FastAPI `BackgroundTasks`.
- Calls Google Geocoding API once; on failure logs and leaves `formatted_address` null.
- One retry with short backoff; gives up after that.

## Rate limiting
- Minimal in-memory rate limiter for `/api/places/*` (no new dependency).
- Limit: e.g. 30 requests per minute per IP.
- Falls back to allowing the request if limiter state is unexpectedly unavailable.

## Tests
- PostGIS search query test with distance assertion.
- Index usage sanity check via EXPLAIN on PostgreSQL (skipped on SQLite).
- ETA cache hit/miss test with mocked Google HTTP call.
- Autocomplete/details field-mask test asserting exact `X-Goog-FieldMask` header.
- Listing creation schedules background reverse-geocode without blocking.
- Static map URL test.

## Files to create/modify
- `app/config.py`
- `app/models/house.py`
- `app/models/eta_cache.py` (new)
- `alembic/versions/...` (new migration)
- `app/clients/google_maps_client.py` (new)
- `app/services/geo_service.py` (new)
- `app/repositories/house_repo.py`
- `app/repositories/eta_cache_repo.py` (new)
- `app/routers/houses.py`
- `app/routers/places.py` (new)
- `app/routers/landlords.py` (background task)
- `app/services/house_service.py` (search/creation changes)
- `app/services/serializers.py`
- `app/schemas/house.py`
- `app/main.py` (register places router)
- `tests/test_geo.py` (new)
- `README.md`
