"""Tests for Lenco payment initiation and webhook processing."""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

from app.config import settings
from tests.conftest import register_user


async def test_mobile_money_payment_and_signed_webhook(client, unique_user_payload):
    student = await register_user(client, unique_user_payload("student"))
    headers = {"Authorization": f"Bearer {student['token']}"}
    payment_response = await client.post(
        "/api/payments/lenco/mobile-money",
        json={"amount": "250.00", "phone": "260971234567", "operator": "airtel"},
        headers=headers,
    )
    assert payment_response.status_code == 200, payment_response.text
    payment = payment_response.json()["data"]
    assert payment["amount"] == "250.00"
    assert payment["status"] == "pay-offline"
    assert payment["lencoReference"].startswith("MOCK-")

    previous_mock = settings.lenco_mock
    previous_secret = settings.lenco_webhook_secret
    settings.lenco_mock = False
    settings.lenco_webhook_secret = "secret"
    try:
        payload = {
            "event": "transaction.successful",
            "data": {"reference": payment["reference"], "status": "successful"},
        }
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        key = hashlib.sha256(b"secret").hexdigest().encode("utf-8")
        signature = hmac.new(key, raw, hashlib.sha512).hexdigest()
        webhook = await client.post(
            "/api/webhooks/lenco",
            content=raw,
            headers={"X-Lenco-Signature": signature},
        )
        assert webhook.status_code == 200, webhook.text
    finally:
        settings.lenco_mock = previous_mock
        settings.lenco_webhook_secret = previous_secret

    status = await client.get(
        f"/api/payments/lenco/{payment['reference']}", headers=headers
    )
    assert status.status_code == 200, status.text
    assert status.json()["data"]["status"] == "successful"


async def test_card_payment_and_3ds_webhook(client, unique_user_payload):
    student = await register_user(client, unique_user_payload("student"))
    headers = {"Authorization": f"Bearer {student['token']}"}
    card_response = await client.post(
        "/api/payments/lenco/card",
        json={
            "amount": "250.00",
            "currency": "ZMW",
            "email": "customer@example.com",
            "customer": {"first_name": "John", "last_name": "Doe"},
            "billing": {
                "street_address": "123 Main St",
                "city": "Lusaka",
                "postal_code": "10101",
                "country": "ZM",
            },
            "card": {
                "number": "5555555555554444",
                "expiry_month": "12",
                "expiry_year": "2025",
                "cvv": "838",
            },
        },
        headers=headers,
    )
    assert card_response.status_code == 200, card_response.text
    payment = card_response.json()["data"]
    assert payment["amount"] == "250.00"
    assert payment["paymentType"] == "card"
    assert payment["status"] == "3ds-auth-required"
    assert payment["meta"]["authorization"]["redirect"].startswith("https://mock")

    previous_mock = settings.lenco_mock
    previous_secret = settings.lenco_webhook_secret
    settings.lenco_mock = False
    settings.lenco_webhook_secret = "secret"
    try:
        payload = {
            "event": "transaction.successful",
            "data": {"reference": payment["reference"], "status": "successful"},
        }
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        key = hashlib.sha256(b"secret").hexdigest().encode("utf-8")
        signature = hmac.new(key, raw, hashlib.sha512).hexdigest()
        webhook = await client.post(
            "/api/webhooks/lenco",
            content=raw,
            headers={"X-Lenco-Signature": signature},
        )
        assert webhook.status_code == 200, webhook.text
    finally:
        settings.lenco_mock = previous_mock
        settings.lenco_webhook_secret = previous_secret

    status = await client.get(
        f"/api/payments/lenco/{payment['reference']}", headers=headers
    )
    assert status.status_code == 200, status.text
    assert status.json()["data"]["status"] == "successful"


async def test_booking_linked_payment_requires_booking_owner(
    client, unique_user_payload
):
    houses = await client.get("/api/houses")
    assert houses.status_code == 200, houses.text
    house_id = houses.json()["data"][0]["id"]

    rooms = await client.get(f"/api/houses/{house_id}/rooms")
    assert rooms.status_code == 200, rooms.text
    room_id = rooms.json()["data"][0]["id"]

    student = await register_user(client, unique_user_payload("student"))
    token = student["token"]

    booking = await client.post(
        "/api/bookings",
        json={
            "house_id": house_id,
            "room_id": room_id,
            "move_in_date": "2026-08-01",
            "note": "payment auth test",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert booking.status_code == 200, booking.text
    booking_id = booking.json()["data"]["id"]

    unauth_payment = await client.post(
        "/api/payments/lenco/mobile-money",
        json={
            "amount": "250.00",
            "phone": "260971234567",
            "operator": "airtel",
            "booking_id": booking_id,
        },
    )
    assert unauth_payment.status_code == 401

    payment_response = await client.post(
        "/api/payments/lenco/mobile-money",
        json={
            "amount": "250.00",
            "phone": "260971234567",
            "operator": "airtel",
            "booking_id": booking_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert payment_response.status_code == 200, payment_response.text
    reference = payment_response.json()["data"]["reference"]

    unauth_status = await client.get(f"/api/payments/lenco/{reference}")
    assert unauth_status.status_code == 401

    other = await register_user(client, unique_user_payload("student"))
    other_status = await client.get(
        f"/api/payments/lenco/{reference}",
        headers={"Authorization": f"Bearer {other['token']}"},
    )
    assert other_status.status_code == 401

    owner_status = await client.get(
        f"/api/payments/lenco/{reference}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert owner_status.status_code == 200


async def test_successful_booking_payment_emails_receipt_to_student(
    client, unique_user_payload
):
    houses = await client.get("/api/houses")
    assert houses.status_code == 200, houses.text
    house_id = houses.json()["data"][0]["id"]

    rooms = await client.get(f"/api/houses/{house_id}/rooms")
    assert rooms.status_code == 200, rooms.text
    room_id = rooms.json()["data"][0]["id"]

    student = await register_user(client, unique_user_payload("student"))
    token = student["token"]

    booking = await client.post(
        "/api/bookings",
        json={
            "house_id": house_id,
            "room_id": room_id,
            "move_in_date": "2026-08-01",
            "note": "receipt send test",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert booking.status_code == 200, booking.text
    booking_id = booking.json()["data"]["id"]

    payment_response = await client.post(
        "/api/payments/lenco/mobile-money",
        json={
            "amount": "250.00",
            "phone": "260971234567",
            "operator": "airtel",
            "booking_id": booking_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert payment_response.status_code == 200, payment_response.text
    reference = payment_response.json()["data"]["reference"]

    previous_mock = settings.lenco_mock
    previous_secret = settings.lenco_webhook_secret
    settings.lenco_mock = False
    settings.lenco_webhook_secret = "secret"
    payload = {
        "event": "transaction.successful",
        "id": "evt-receipt-test",
        "data": {"reference": reference, "status": "successful"},
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    key = hashlib.sha256(b"secret").hexdigest().encode("utf-8")
    signature = hmac.new(key, raw, hashlib.sha512).hexdigest()
    try:
        with patch(
            "app.services.payment_service.send_booking_receipt_email",
            new_callable=AsyncMock,
        ) as send_receipt:
            send_receipt.return_value = True
            webhook = await client.post(
                "/api/webhooks/lenco",
                content=raw,
                headers={"X-Lenco-Signature": signature},
            )
            duplicate = await client.post(
                "/api/webhooks/lenco",
                content=raw,
                headers={"X-Lenco-Signature": signature},
            )
    finally:
        settings.lenco_mock = previous_mock
        settings.lenco_webhook_secret = previous_secret

    assert webhook.status_code == 200, webhook.text
    assert duplicate.status_code == 200, duplicate.text
    send_receipt.assert_awaited_once()
    args, kwargs = send_receipt.await_args
    assert args[0] == student["user"]["email"]
    assert kwargs["pdf_bytes"].startswith(b"%PDF")
    assert kwargs["filename"].endswith(".pdf")
