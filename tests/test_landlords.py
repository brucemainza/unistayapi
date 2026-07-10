"""Tests for landlord management endpoints."""

from tests.conftest import register_user


async def test_landlord_house_room_payment_details_and_booking_flow(
    client, unique_user_payload
):
    landlord = await register_user(client, unique_user_payload("landlord"))
    landlord_headers = {"Authorization": f"Bearer {landlord['token']}"}

    created = await client.post(
        "/api/landlords/houses",
        headers=landlord_headers,
        json={
            "name": "Landlord Test House",
            "location": "Lusaka",
            "price": 1300,
            "available_spaces": 2,
            "amenities": ["WiFi"],
            "rooms": [{"type": "Single", "rent": 1300, "available": 2}],
        },
    )
    assert created.status_code == 200, created.text
    house = created.json()["data"]

    houses = await client.get("/api/landlords/me/houses", headers=landlord_headers)
    assert houses.status_code == 200, houses.text
    assert any(item["id"] == house["id"] for item in houses.json()["data"])

    room = await client.post(
        f"/api/landlords/houses/{house['id']}/rooms",
        headers=landlord_headers,
        json={"type": "Shared", "rent": 900, "available": 1},
    )
    assert room.status_code == 200, room.text

    amenities = await client.patch(
        f"/api/landlords/houses/{house['id']}/amenities",
        headers=landlord_headers,
        json={"amenities": ["WiFi", "Security"]},
    )
    assert amenities.status_code == 200, amenities.text
    assert amenities.json()["data"]["amenities"] == ["WiFi", "Security"]

    details = await client.put(
        "/api/landlords/payment-details",
        headers=landlord_headers,
        json={"mobile_money_provider": "airtel", "mobile_money_number": "260971234567"},
    )
    assert details.status_code == 200, details.text
    assert details.json()["data"]["mobileMoneyProvider"] == "airtel"

    rooms = await client.get(f"/api/houses/{house['id']}/rooms")
    student = await register_user(client, unique_user_payload("student"))
    booking = await client.post(
        "/api/bookings",
        headers={"Authorization": f"Bearer {student['token']}"},
        json={
            "house_id": house["id"],
            "room_id": rooms.json()["data"][0]["id"],
            "move_in_date": "2026-08-01",
        },
    )
    assert booking.status_code == 200, booking.text

    landlord_bookings = await client.get(
        "/api/landlords/bookings", headers=landlord_headers
    )
    assert landlord_bookings.status_code == 200, landlord_bookings.text
    assert len(landlord_bookings.json()["data"]) == 1

    status = await client.patch(
        f"/api/landlords/bookings/{booking.json()['data']['id']}/status",
        headers=landlord_headers,
        json={"status": "confirmed"},
    )
    assert status.status_code == 200, status.text
    assert status.json()["data"]["status"] == "confirmed"
