"""Tests for notification endpoints."""

from app.models.notification import Notification

from tests.conftest import register_user


async def test_notifications_list_and_mark_read(client, db_sessionmaker, unique_user_payload):
    user = await register_user(client, unique_user_payload("student"))
    async with db_sessionmaker() as session:
        session.add(
            Notification(
                user_id=user["user"]["id"],
                title="Hello",
                body="Welcome to UniStay",
            )
        )
        await session.commit()

    headers = {"Authorization": f"Bearer {user['token']}"}
    listing = await client.get("/api/notifications", headers=headers)
    assert listing.status_code == 200, listing.text
    notification = listing.json()["data"][0]
    assert notification["isRead"] is False

    read = await client.patch(
        f"/api/notifications/{notification['id']}/read", headers=headers
    )
    assert read.status_code == 200, read.text
    assert read.json()["data"]["isRead"] is True

    read_all = await client.patch("/api/notifications/read-all", headers=headers)
    assert read_all.status_code == 200, read_all.text
    assert "updated" in read_all.json()["data"]
