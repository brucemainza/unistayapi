"""Tests for favorite houses."""

from tests.conftest import register_user


async def test_favorite_add_list_remove(client, unique_user_payload):
    token = (await register_user(client, unique_user_payload("student")))["token"]
    headers = {"Authorization": f"Bearer {token}"}
    house = (await client.get("/api/houses")).json()["data"][0]

    added = await client.post(
        "/api/favorites", json={"house_id": house["id"]}, headers=headers
    )
    assert added.status_code == 200, added.text
    assert added.json()["data"]["id"] == house["id"]

    listing = await client.get("/api/favorites", headers=headers)
    assert listing.status_code == 200, listing.text
    assert [item["id"] for item in listing.json()["data"]] == [house["id"]]

    removed = await client.delete(f"/api/favorites/{house['id']}", headers=headers)
    assert removed.status_code == 200, removed.text
    assert removed.json()["data"] is None
