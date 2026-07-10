"""Tests for the user profile endpoints."""

import random

import httpx
import pytest
from httpx import ASGITransport

from app.main import app


@pytest.fixture
def unique_user():
    suffix = random.randint(1_000_000_000, 9_999_999_999)
    return {
        "full_name": "Test User",
        "phone": str(suffix),
        "email": f"test_{suffix}@example.com",
        "password": "secret123",
        "role": "student",
    }


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as c:
        yield c


@pytest.fixture
async def auth_token(client, unique_user):
    response = await client.post("/api/auth/register", json=unique_user)
    assert response.status_code == 200, response.text
    return response.json()["data"]["token"]


async def test_get_me_returns_current_user(client, auth_token, unique_user):
    response = await client.get(
        "/api/users/me", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] is True
    assert data["message"] == "User profile"
    assert data["data"]["email"] == unique_user["email"]
    assert data["data"]["phone"] == unique_user["phone"]
    assert data["data"]["role"] == unique_user["role"]
    assert "id" in data["data"]


async def test_update_me_updates_profile(client, auth_token, unique_user):
    new_suffix = random.randint(1_000_000_000, 9_999_999_999)
    update_payload = {
        "full_name": "Updated Name",
        "email": f"updated_{new_suffix}@example.com",
    }
    response = await client.patch(
        "/api/users/me",
        json=update_payload,
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] is True
    assert data["message"] == "Profile updated"
    assert data["data"]["full_name"] == update_payload["full_name"]
    assert data["data"]["email"] == update_payload["email"]
    assert data["data"]["phone"] == unique_user["phone"]
    assert data["data"]["role"] == unique_user["role"]


async def test_get_stats_returns_placeholder_counts(client, auth_token):
    response = await client.get(
        "/api/users/me/stats", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] is True
    assert data["message"] == "User stats"
    assert data["data"]["bookings_count"] == 0
    assert data["data"]["favorites_count"] == 0
    assert data["data"]["payments_count"] == 0


async def test_get_accommodation_returns_placeholder(client, auth_token):
    response = await client.get(
        "/api/users/me/accommodation",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] is True
    assert data["message"] == "User accommodation"
    assert data["data"]["current_booking"] is None
    assert data["data"]["current_house"] is None


async def test_me_endpoints_require_authentication(client):
    for path in ["/api/users/me", "/api/users/me/stats", "/api/users/me/accommodation"]:
        response = await client.get(path)
        assert response.status_code == 401, f"{path} should require auth"
        data = response.json()
        assert data["status"] is False

    response = await client.patch("/api/users/me", json={"full_name": "No Auth"})
    assert response.status_code == 401
    assert response.json()["status"] is False
