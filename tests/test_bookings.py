"""Tests for booking creation and capacity protection."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.models.payment import Payment
from tests.conftest import register_user


async def _create_landlord_house(client, token: str) -> dict:
    response = await client.post(
        "/api/landlords/houses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Capacity Test House",
            "location": "Test Area",
            "price": 1000,
            "available_spaces": 1,
            "latitude": -15.39,
            "longitude": 28.33,
            "rooms": [
                {
                    "type": "Single",
                    "rent": 1000,
                    "deposit": 500,
                    "available": 1,
                    "features": ["Desk"],
                }
            ],
        },
    )
    assert response.status_code == 200, response.text
    house = response.json()["data"]
    rooms = await client.get(f"/api/houses/{house['id']}/rooms")
    house["room"] = rooms.json()["data"][0]
    return house


async def test_booking_create_receipt_and_double_booking_prevention(
    client, unique_user_payload, db_sessionmaker
):
    landlord = await register_user(client, unique_user_payload("landlord"))
    house = await _create_landlord_house(client, landlord["token"])

    student = await register_user(client, unique_user_payload("student"))
    headers = {"Authorization": f"Bearer {student['token']}"}
    payload = {
        "house_id": house["id"],
        "room_id": house["room"]["id"],
        "move_in_date": "2026-08-01",
    }
    first = await client.post("/api/bookings", json=payload, headers=headers)
    assert first.status_code == 200, first.text
    booking_id = first.json()["data"]["id"]

    receipt = await client.get(f"/api/bookings/{booking_id}/receipt", headers=headers)
    assert receipt.status_code == 200, receipt.text
    assert receipt.json()["data"]["booking"]["id"] == booking_id
    assert receipt.json()["data"]["studentEmail"] == student["user"]["email"]

    pdf = await client.get(f"/api/bookings/{booking_id}/receipt.pdf", headers=headers)
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")

    with patch(
        "app.services.booking_service.send_booking_receipt_email",
        new_callable=AsyncMock,
    ) as send_receipt:
        emailed = await client.post(
            f"/api/bookings/{booking_id}/receipt/email", headers=headers
        )
    assert emailed.status_code == 422
    send_receipt.assert_not_awaited()

    async with db_sessionmaker() as db:
        db.add(
            Payment(
                reference="TEST-RECEIPT-PAID",
                booking_id=booking_id,
                user_id=student["user"]["id"],
                amount=Decimal("2500.00"),
                currency="ZMW",
                payment_type="mobile-money",
                operator="mtn",
                phone=student["user"]["phone"],
                status="successful",
                payload={"source": "test"},
            )
        )
        await db.commit()

    with patch(
        "app.services.booking_service.send_booking_receipt_email",
        new_callable=AsyncMock,
    ) as send_receipt:
        send_receipt.return_value = True
        emailed = await client.post(
            f"/api/bookings/{booking_id}/receipt/email", headers=headers
        )
    assert emailed.status_code == 200, emailed.text
    assert emailed.json()["data"]["email"] == student["user"]["email"]
    assert emailed.json()["data"]["filename"].endswith(".pdf")
    send_receipt.assert_awaited_once()
    _, kwargs = send_receipt.await_args
    assert kwargs["pdf_bytes"].startswith(b"%PDF")
    assert kwargs["filename"].endswith(".pdf")

    second_student = await register_user(client, unique_user_payload("student"))
    second = await client.post(
        "/api/bookings",
        json=payload,
        headers={"Authorization": f"Bearer {second_student['token']}"},
    )
    assert second.status_code == 409
    assert second.json()["status"] is False
