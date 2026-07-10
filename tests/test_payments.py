"""Tests for Lenco payment initiation and webhook processing."""

import hashlib
import hmac
import json

from app.config import settings


async def test_mobile_money_payment_and_signed_webhook(client):
    payment_response = await client.post(
        "/api/payments/lenco/mobile-money",
        json={"amount": "250.00", "phone": "260971234567", "operator": "airtel"},
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

    status = await client.get(f"/api/payments/lenco/{payment['reference']}")
    assert status.status_code == 200, status.text
    assert status.json()["data"]["status"] == "successful"
