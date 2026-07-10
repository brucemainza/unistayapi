"""Tests for booking creation and capacity protection."""

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
    client, unique_user_payload
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

    second_student = await register_user(client, unique_user_payload("student"))
    second = await client.post(
        "/api/bookings",
        json=payload,
        headers={"Authorization": f"Bearer {second_student['token']}"},
    )
    assert second.status_code == 409
    assert second.json()["status"] is False
