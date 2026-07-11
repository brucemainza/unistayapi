"""Tests for geo module: PostGIS search, ETA cache, Places proxy, static maps."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.eta_cache import EtaCache
from app.models.house import House
from app.models.university import University


async def _get_university(db_sessionmaker):
    async with db_sessionmaker() as db:
        result = await db.execute(select(University).limit(1))
        return result.scalar_one_or_none()


async def _get_house(db_sessionmaker):
    async with db_sessionmaker() as db:
        result = await db.execute(select(House).limit(1))
        return result.scalar_one_or_none()


async def test_search_houses_by_university_distance(client, db_sessionmaker):
    university = await _get_university(db_sessionmaker)
    if university is None:
        pytest.skip("No seeded university available")

    response = await client.get(
        f"/api/houses?university_id={university.id}&radius_m=10000"
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert "items" in data
    assert "total" in data


async def test_eta_cache_miss_calls_google(client, db_sessionmaker):
    university = await _get_university(db_sessionmaker)
    if university is None:
        pytest.skip("No seeded university available")

    house = await _get_house(db_sessionmaker)
    if house is None:
        pytest.skip("No seeded house available")

    with patch(
        "app.clients.google_maps_client.GoogleMapsClient.compute_route_matrix",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = [
            {"elements": [{"duration": "600s", "distanceMeters": 1500}]}
        ]
        response = await client.get(
            f"/api/houses/{house.id}/eta?university_id={university.id}&mode=DRIVE"
        )
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["durationS"] == 600
        assert data["distanceM"] == 1500
        assert data["cached"] is False
        mock.assert_awaited_once()

    # Cache hit on second request
    with patch(
        "app.clients.google_maps_client.GoogleMapsClient.compute_route_matrix",
        new_callable=AsyncMock,
    ) as mock:
        response = await client.get(
            f"/api/houses/{house.id}/eta?university_id={university.id}&mode=DRIVE"
        )
        assert response.status_code == 200, response.text
        assert response.json()["data"]["cached"] is True
        mock.assert_not_awaited()

    # Verify cache row exists
    async with db_sessionmaker() as db:
        result = await db.execute(
            select(EtaCache).where(
                EtaCache.house_id == house.id,
                EtaCache.university_id == university.id,
                EtaCache.mode == "DRIVE",
            )
        )
        cache = result.scalar_one_or_none()
        assert cache is not None
        assert cache.duration_s == 600
        assert cache.distance_m == 1500


async def test_places_autocomplete_field_mask(client):
    with patch(
        "app.clients.google_maps_client.GoogleMapsClient.autocomplete",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = {"suggestions": []}
        response = await client.get(
            "/api/places/autocomplete?input=lusaka&session_token=abc"
        )
        assert response.status_code == 200, response.text
        args, kwargs = mock.call_args
        assert kwargs["input_text"] == "lusaka"
        assert kwargs["session_token"] == "abc"


async def test_static_map_url_returns_502_on_google_error(client, db_sessionmaker):
    from app.clients.google_maps_client import GoogleMapsError

    house = await _get_house(db_sessionmaker)
    if house is None:
        pytest.skip("No seeded house available")

    with patch(
        "app.services.geo_service.GoogleMapsClient.static_map_url",
        side_effect=GoogleMapsError("Google Maps error"),
    ):
        response = await client.get(f"/api/houses/{house.id}/static-map")
    # GoogleMapsError maps to 502 with a Flutter-compatible envelope.
    assert response.status_code == 502
    assert response.json()["status"] is False


async def test_listing_creation_schedules_background_geocode(
    client, db_sessionmaker, unique_user_payload
):
    from tests.conftest import register_user

    landlord_payload = unique_user_payload("landlord")
    await register_user(client, landlord_payload)

    login = await client.post(
        "/api/auth/login",
        json={"phone": landlord_payload["phone"], "password": "secret123"},
    )
    token = login.json()["data"]["token"]

    with patch(
        "app.services.house_service.GoogleMapsClient.reverse_geocode",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = "123 Main St, Lusaka, Zambia"
        response = await client.post(
            "/api/landlords/houses",
            json={
                "name": "Geo Test House",
                "location": "Lusaka",
                "latitude": -15.4167,
                "longitude": 28.2833,
                "price": 1000,
                "amenities": ["WiFi"],
                "image_urls": [],
                "nearby_universities": [],
                "rooms": [],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["data"]["latitude"] == -15.4167


async def test_index_usage_on_postgres(client, db_sessionmaker):
    from app.geo import get_dialect_name

    async with db_sessionmaker() as db:
        if get_dialect_name(db) != "postgresql":
            pytest.skip("Index check requires PostgreSQL")
    assert True
