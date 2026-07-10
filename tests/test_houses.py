"""Tests for house search and details."""


async def test_houses_detail_rooms_similar_and_nearby(client):
    listing = await client.get("/api/houses")
    assert listing.status_code == 200, listing.text
    houses = listing.json()["data"]
    assert len(houses) >= 2
    first = houses[0]
    assert {"imageUrls", "paymentMethods", "nearbyUniversities", "availableSpaces"} <= set(first)

    detail = await client.get(f"/api/houses/{first['id']}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["data"]["id"] == first["id"]

    rooms = await client.get(f"/api/houses/{first['id']}/rooms")
    assert rooms.status_code == 200, rooms.text
    assert len(rooms.json()["data"]) >= 1

    similar = await client.get(f"/api/houses/{first['id']}/similar")
    assert similar.status_code == 200, similar.text
    assert isinstance(similar.json()["data"], list)

    nearby = await client.get(
        "/api/houses/nearby",
        params={"latitude": -15.3918, "longitude": 28.3296, "radius_km": 10},
    )
    assert nearby.status_code == 200, nearby.text
    assert len(nearby.json()["data"]) >= 1
