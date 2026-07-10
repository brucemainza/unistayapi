"""Smoke tests for the authentication endpoints."""

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
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def test_register_returns_token_and_user(client, unique_user):
    response = await client.post("/api/auth/register", json=unique_user)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] is True
    assert data["message"] == "Registration successful"
    assert "token" in data["data"]
    user = data["data"]["user"]
    assert user["email"] == unique_user["email"]
    assert user["phone"] == unique_user["phone"]
    assert user["role"] == unique_user["role"]
    assert "id" in user


async def test_login_returns_token_and_user(client, unique_user):
    await client.post("/api/auth/register", json=unique_user)
    response = await client.post(
        "/api/auth/login",
        json={"phone": unique_user["phone"], "password": unique_user["password"]},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] is True
    assert "token" in data["data"]
    assert data["data"]["user"]["phone"] == unique_user["phone"]


async def test_me_returns_current_user(client, unique_user):
    register_response = await client.post("/api/auth/register", json=unique_user)
    token = register_response.json()["data"]["token"]
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] is True
    assert data["data"]["email"] == unique_user["email"]


async def test_dev_token_resolves_to_dev_user(client):
    response = await client.get(
        "/api/auth/me", headers={"Authorization": "Bearer dev-student-token"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] is True
    assert data["data"]["role"] == "student"


async def test_verify_otp_mock_mode_accepts_any_five_digit_code(client, unique_user):
    register_response = await client.post("/api/auth/register", json=unique_user)
    user = register_response.json()["data"]["user"]
    response = await client.post(
        "/api/auth/verify-otp",
        json={"user_id": user["id"], "code": "12345"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] is True
    assert data["data"]["user"]["is_verified"] is True


async def test_resend_otp_returns_code(client, unique_user):
    register_response = await client.post("/api/auth/register", json=unique_user)
    user = register_response.json()["data"]["user"]
    response = await client.post("/api/auth/resend-otp", json={"user_id": user["id"]})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] is True
    assert "code" in data["data"]
    assert len(data["data"]["code"]) == 5
