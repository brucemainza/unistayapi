"""Tests for authentication endpoints."""

from tests.conftest import register_user


async def test_register_login_me_and_dev_token(client, unique_user_payload):
    payload = unique_user_payload("student")
    registered = await register_user(client, payload)
    assert registered["user"]["email"] == payload["email"]
    assert registered["user"]["is_verified"] is False
    assert registered["token"]

    login = await client.post(
        "/api/auth/login",
        json={"phone": payload["phone"], "password": payload["password"]},
    )
    assert login.status_code == 200, login.text
    assert login.json()["data"]["user"]["phone"] == payload["phone"]

    me = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {registered['token']}"},
    )
    assert me.status_code == 200, me.text
    assert me.json()["data"]["email"] == payload["email"]

    dev = await client.get(
        "/api/auth/me", headers={"Authorization": "Bearer dev-student-token"}
    )
    assert dev.status_code == 200, dev.text
    assert dev.json()["data"]["role"] == "student"


async def test_otp_and_validation_errors_use_envelope(client, unique_user_payload):
    registered = await register_user(client, unique_user_payload("student"))
    user_id = registered["user"]["id"]

    verify = await client.post(
        "/api/auth/verify-otp", json={"user_id": user_id, "code": "12345"}
    )
    assert verify.status_code == 200, verify.text
    assert verify.json()["data"]["user"]["is_verified"] is True

    resend = await client.post("/api/auth/resend-otp", json={"user_id": user_id})
    assert resend.status_code == 200, resend.text
    assert len(resend.json()["data"]["code"]) == 5

    invalid = await client.post("/api/auth/register", json={"phone": "bad"})
    assert invalid.status_code == 422
    assert invalid.json()["status"] is False
    assert invalid.json()["data"] is None
