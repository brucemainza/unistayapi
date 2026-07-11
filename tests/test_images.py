"""Tests for Cloudinary image upload endpoints."""

from unittest.mock import AsyncMock, patch

from tests.conftest import register_user


async def _get_auth_header(client, unique_user_payload):
    payload = unique_user_payload("landlord")
    registered = await register_user(client, payload)
    return {"Authorization": f"Bearer {registered['token']}"}


async def test_upload_image_returns_cloudinary_url(client, unique_user_payload):
    headers = await _get_auth_header(client, unique_user_payload)

    with patch(
        "app.routers.images.cloudinary_client.upload_image",
        new_callable=AsyncMock,
    ) as mock_upload:
        mock_upload.return_value = "https://res.cloudinary.com/demo/image/upload/test.jpg"
        response = await client.post(
            "/api/images/upload",
            headers=headers,
            files={"file": ("house.jpg", b"fake-image-bytes", "image/jpeg")},
        )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["url"] == mock_upload.return_value
    mock_upload.assert_awaited_once()


async def test_upload_multiple_images_returns_urls(client, unique_user_payload):
    headers = await _get_auth_header(client, unique_user_payload)

    with patch(
        "app.routers.images.cloudinary_client.upload_image",
        new_callable=AsyncMock,
    ) as mock_upload:
        mock_upload.side_effect = [
            "https://res.cloudinary.com/demo/image/upload/1.jpg",
            "https://res.cloudinary.com/demo/image/upload/2.jpg",
        ]
        response = await client.post(
            "/api/images/upload-multiple",
            headers=headers,
            files=[
                ("files", ("a.jpg", b"a", "image/jpeg")),
                ("files", ("b.jpg", b"b", "image/jpeg")),
            ],
        )

    assert response.status_code == 200, response.text
    assert len(response.json()["data"]["urls"]) == 2
    assert mock_upload.await_count == 2


async def test_upload_rejects_invalid_content_type(client, unique_user_payload):
    headers = await _get_auth_header(client, unique_user_payload)

    response = await client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("house.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 422
    assert response.json()["status"] is False


async def test_upload_rejects_oversized_image(client, unique_user_payload):
    headers = await _get_auth_header(client, unique_user_payload)

    response = await client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("huge.jpg", b"x" * (5 * 1024 * 1024 + 1), "image/jpeg")},
    )
    assert response.status_code == 422
    assert response.json()["status"] is False


async def test_upload_requires_authentication(client):
    response = await client.post(
        "/api/images/upload",
        files={"file": ("house.jpg", b"fake", "image/jpeg")},
    )
    assert response.status_code == 401
    assert response.json()["status"] is False
