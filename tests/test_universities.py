"""Tests for the universities listing endpoint."""

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import async_session
from app.main import app
from app.seed import seed_universities


@pytest.fixture(scope="session")
async def seeded_universities():
    """Ensure the test database contains the default Zambian universities."""
    async with async_session() as db:
        universities = await seed_universities(db)
        yield universities


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as c:
        yield c


async def test_list_universities_returns_seed_data(client, seeded_universities):
    response = await client.get("/api/universities")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] is True
    assert data["message"] == "Universities retrieved"
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 5

    for item in data["data"]:
        assert "id" in item
        assert "name" in item
        assert "initials" in item
        assert "latitude" in item
        assert "longitude" in item
        assert isinstance(item["latitude"], float)
        assert isinstance(item["longitude"], float)

    names = {item["name"] for item in data["data"]}
    assert "University of Zambia" in names
    assert "Copperbelt University" in names


async def test_university_response_has_valid_coordinates(client, seeded_universities):
    response = await client.get("/api/universities")
    assert response.status_code == 200, response.text
    data = response.json()

    by_initials = {item["initials"]: item for item in data["data"]}
    assert "UNZA" in by_initials
    unza = by_initials["UNZA"]
    assert -16.0 < unza["latitude"] < -14.0
    assert 27.0 < unza["longitude"] < 29.0
