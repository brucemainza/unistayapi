"""Tests for user profile endpoints."""

from tests.conftest import register_user


async def test_user_profile_update_stats_and_accommodation(client, unique_user_payload):
    payload = unique_user_payload("student")
    registered = await register_user(client, payload)
    token = registered["token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/users/me", headers=headers)
    assert me.status_code == 200, me.text
    assert me.json()["message"] == "User profile"
    assert me.json()["data"]["email"] == payload["email"]

    updated = await client.patch(
        "/api/users/me",
        json={"full_name": "Updated Student"},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["full_name"] == "Updated Student"

    stats = await client.get("/api/users/me/stats", headers=headers)
    assert stats.status_code == 200, stats.text
    assert stats.json()["data"] == {
        "bookings_count": 0,
        "favorites_count": 0,
        "payments_count": 0,
    }

    accommodation = await client.get("/api/users/me/accommodation", headers=headers)
    assert accommodation.status_code == 200, accommodation.text
    assert accommodation.json()["data"]["current_booking"] is None
    assert accommodation.json()["data"]["current_house"] is None


async def test_user_endpoints_require_authentication(client):
    response = await client.get("/api/users/me")
    assert response.status_code == 401
    assert response.json()["status"] is False
