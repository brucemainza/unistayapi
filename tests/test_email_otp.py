"""Tests for email OTP verification (Redis + Resend)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.config import settings
from app.exceptions import RateLimitError
from app.services.email import send_otp_email
from app.services.otp import issue_otp, verify_otp


@pytest.fixture
def email():
    return "otp-test@example.com"


async def test_issue_otp_stores_hash_and_cooldown(fake_redis, email):
    code = await issue_otp(fake_redis, email)
    assert len(code) == 6
    assert code.isdigit()

    stored = await fake_redis.get(f"otp:{email}")
    assert stored is not None

    cooldown = await fake_redis.exists(f"otp:cooldown:{email}")
    assert cooldown


async def test_issue_otp_respects_cooldown(fake_redis, email):
    await issue_otp(fake_redis, email)
    with pytest.raises(RateLimitError):
        await issue_otp(fake_redis, email)


async def test_issue_otp_clears_attempts(fake_redis, email):
    await fake_redis.set(f"otp:attempts:{email}", "3")
    await issue_otp(fake_redis, email)
    attempts = await fake_redis.exists(f"otp:attempts:{email}")
    assert not attempts


async def test_verify_otp_success(fake_redis, email):
    code = await issue_otp(fake_redis, email)
    assert await verify_otp(fake_redis, email, code) is True

    assert await fake_redis.exists(f"otp:{email}") == 0
    assert await fake_redis.exists(f"otp:attempts:{email}") == 0


async def test_verify_otp_wrong_code(fake_redis, email):
    await issue_otp(fake_redis, email)
    assert await verify_otp(fake_redis, email, "000000") is False


async def test_verify_otp_attempts_limit(fake_redis, email):
    await issue_otp(fake_redis, email)
    for _ in range(5):
        await verify_otp(fake_redis, email, "000000")
    with pytest.raises(RateLimitError):
        await verify_otp(fake_redis, email, "000000")


async def test_send_otp_email_reports_resend_errors(email, monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "test-key")
    with patch("app.services.email.resend.Emails.send") as mock_send:
        mock_send.side_effect = RuntimeError("boom")
        assert await send_otp_email(email, "123456") is False


async def test_send_otp_email_calls_resend_with_expected_args(email, monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "test-key")
    with patch("app.services.email.resend.Emails.send") as mock_send:
        assert await send_otp_email(email, "123456") is True
        mock_send.assert_called_once()
        params = mock_send.call_args.args[0]
        assert params["from"] == settings.resend_from_email
        assert params["to"] == email
        assert "123456" in params["html"]


async def test_signup_returns_201_after_resend_accepts_email(client, unique_user_payload):
    payload = unique_user_payload("student")

    with patch("app.routers.auth.send_otp_email", new_callable=AsyncMock) as mock_email:
        mock_email.return_value = True
        response = await client.post("/api/auth/signup", json=payload)
        assert response.status_code == 201, response.text
        data = response.json()["data"]
        assert data["email"] == payload["email"]
        assert "id" in data
        mock_email.assert_called_once()


async def test_signup_returns_502_when_resend_rejects_delivery(client, unique_user_payload):
    with patch("app.routers.auth.send_otp_email", new_callable=AsyncMock) as mock_email:
        mock_email.return_value = False
        response = await client.post("/api/auth/signup", json=unique_user_payload("student"))

    assert response.status_code == 502
    assert response.json()["status"] is False


async def test_signup_rate_limit_blocks_after_five_attempts(client, unique_user_payload):
    with patch("app.routers.auth.send_otp_email", new_callable=AsyncMock):
        for i in range(5):
            payload = unique_user_payload("student")
            payload["email"] = f"ratelim{i}_{payload['email']}"
            payload["phone"] = str(int(payload["phone"]) + i)
            response = await client.post("/api/auth/signup", json=payload)
            assert response.status_code == 201, response.text

        payload = unique_user_payload("student")
        response = await client.post("/api/auth/signup", json=payload)
        assert response.status_code == 429
        assert response.json()["status"] is False


async def test_verify_email_and_resend_email_otp(client, unique_user_payload, fake_redis):
    payload = unique_user_payload("student")
    captured: dict[str, str] = {}

    async def capture_issue_otp(redis, email):
        code = await issue_otp(redis, email)
        captured["code"] = code
        return code

    with patch("app.routers.auth.issue_otp", side_effect=capture_issue_otp):
        with patch("app.routers.auth.send_otp_email", new_callable=AsyncMock):
            signup = await client.post("/api/auth/signup", json=payload)
            assert signup.status_code == 201

    code = captured["code"]
    verify = await client.post(
        "/api/auth/verify-email",
        json={"email": payload["email"], "code": code},
    )
    assert verify.status_code == 200, verify.text
    assert verify.json()["data"]["user"]["email_verified"] is True

    # Clear the signup cooldown so the resend endpoint can issue a fresh code.
    await fake_redis.delete(f"otp:cooldown:{payload['email']}")
    captured.pop("code", None)

    with patch("app.routers.auth.issue_otp", side_effect=capture_issue_otp):
        with patch("app.routers.auth.send_otp_email", new_callable=AsyncMock):
            resend = await client.post(
                "/api/auth/resend-email-otp", json={"email": payload["email"]}
            )
            assert resend.status_code == 200, resend.text

    code2 = captured.get("code")
    assert code2 is not None
    verify2 = await client.post(
        "/api/auth/verify-email",
        json={"email": payload["email"], "code": code2},
    )
    assert verify2.status_code == 200


async def test_verify_email_rejects_wrong_code(client, unique_user_payload):
    payload = unique_user_payload("student")

    with patch("app.routers.auth.send_otp_email", new_callable=AsyncMock):
        await client.post("/api/auth/signup", json=payload)

    response = await client.post(
        "/api/auth/verify-email",
        json={"email": payload["email"], "code": "000000"},
    )
    assert response.status_code == 401
    assert response.json()["status"] is False
    assert response.json()["message"] == "Invalid or expired code"
