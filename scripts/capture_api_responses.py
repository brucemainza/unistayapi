#!/usr/bin/env python3
"""Capture real API responses from the UniStay app for API_REFERENCE.md.

When ``BASE_URL`` is not set the script runs the app against an in-memory
SQLite database (same setup as the pytest suite). When ``BASE_URL`` points to
a live deployment (e.g. ``https://unistay-api.onrender.com``) the script sends
requests over the network and captures the real production responses including
Postgres-correct timestamps and PostGIS distances.
"""

import asyncio
import io
import json
import os
import random
import sys
import traceback
from pathlib import Path

import fakeredis
import httpx
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.models  # noqa: F401 - register SQLAlchemy models
from app.config import settings
from app.dependencies import get_db, get_redis
from app.main import app
from app.models.base import Base
from app.seed import seed_sample_data


class Recorder:
    def __init__(self, path: Path):
        self.path = path
        self.records = []

    def add(self, method: str, path: str, status: int, request_body, response_body, notes: str = ""):
        rec = {
            "method": method,
            "path": path,
            "status": status,
            "request": request_body,
            "response": response_body,
            "notes": notes,
        }
        self.records.append(rec)
        self._flush()

    def add_error(self, method: str, path: str, request_body, exception: Exception, notes: str = ""):
        rec = {
            "method": method,
            "path": path,
            "status": None,
            "request": request_body,
            "response": {"exception": type(exception).__name__, "detail": str(exception)},
            "notes": notes or "uncaught exception",
        }
        self.records.append(rec)
        self._flush()

    def _flush(self):
        self.path.write_text(json.dumps(self.records, indent=2, default=str), encoding="utf-8")


async def capture():
    base_url = os.getenv("BASE_URL")
    output_path = Path(__file__).parent / "captured_responses.json"
    rec = Recorder(output_path)

    async def call(method: str, url: str, *, request_body=None, files=None, headers=None, notes=""):
        try:
            if method == "GET":
                r = await client.get(url, headers=headers)
            elif method == "POST":
                if files:
                    r = await client.post(url, files=files, headers=headers)
                elif request_body and isinstance(request_body, (bytes,)):
                    r = await client.post(url, content=request_body, headers=headers)
                else:
                    r = await client.post(url, json=request_body, headers=headers)
            elif method == "PATCH":
                r = await client.patch(url, json=request_body, headers=headers)
            elif method == "PUT":
                r = await client.put(url, json=request_body, headers=headers)
            elif method == "DELETE":
                r = await client.delete(url, headers=headers)
            else:
                raise ValueError(method)

            try:
                body = r.json()
            except Exception:
                body = r.text
            rec.add(method, url, r.status_code, request_body, body, notes)
            return r
        except Exception as exc:
            rec.add_error(method, url, request_body, exc, notes)
            return None

    if base_url:
        # Remote mode: capture against a live Render / local deployment.
        print(f"Capturing against remote base URL: {base_url}")
        async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
            await _capture_all(call)
        print(f"Captured {len(rec.records)} responses to {output_path}")
        return

    # Local in-memory mode: same setup as the pytest suite.
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        await seed_sample_data(session)

    async def override_get_db() -> AsyncSession:
        async with sessionmaker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    fake_redis = fakeredis.FakeAsyncRedis(decode_responses=True)

    async def override_get_redis():
        yield fake_redis

    previous_env = settings.environment
    previous_mock = settings.lenco_mock
    settings.environment = "test"
    settings.lenco_mock = True
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            await _capture_all(call)
    finally:
        app.dependency_overrides.clear()
        settings.environment = previous_env
        settings.lenco_mock = previous_mock
        await engine.dispose()

    print(f"Captured {len(rec.records)} responses to {output_path}")


async def _capture_all(call):
    """Shared capture logic — works against local ASGI or remote BASE_URL."""
    # Health / OpenAPI
    await call("GET", "/api/health")
    await call("GET", "/openapi.json", notes="schema only")

    # Auth - register student
    suffix = random.randint(1_000_000_000, 9_999_999_999)
    student_payload = {
        "full_name": f"Test Student {suffix}",
        "phone": str(suffix),
        "email": f"student_{suffix}@example.com",
        "password": "secret123",
        "role": "student",
    }
    r = await call("POST", "/api/auth/register", request_body=student_payload)
    if r and r.status_code == 200:
        student_token = r.json()["data"]["token"]
        student_id = r.json()["data"]["user"]["id"]
    else:
        student_token = ""
        student_id = ""

    # Auth - login
    await call("POST", "/api/auth/login", request_body={"phone": student_payload["phone"], "password": "secret123"})

    # Auth - me / missing auth
    await call("GET", "/api/auth/me", headers={"Authorization": f"Bearer {student_token}"})
    await call("GET", "/api/auth/me", notes="missing auth")

    # Auth - register landlord
    landlord_suffix = random.randint(1_000_000_000, 9_999_999_999)
    landlord_payload = {
        "full_name": f"Test Landlord {landlord_suffix}",
        "phone": str(landlord_suffix),
        "email": f"landlord_{landlord_suffix}@example.com",
        "password": "secret123",
        "role": "landlord",
    }
    r = await call("POST", "/api/auth/register", request_body=landlord_payload, notes="landlord")
    if r and r.status_code == 200:
        landlord_token = r.json()["data"]["token"]
    else:
        landlord_token = ""

    # Auth - verify-otp (mock mode accepts any 5-digit code)
    await call("POST", "/api/auth/verify-otp", request_body={"user_id": student_id, "code": "12345"})

    # Auth - resend-otp
    await call("POST", "/api/auth/resend-otp", request_body={"user_id": student_id})

    # Auth - signup with email OTP
    signup_suffix = random.randint(1_000_000_000, 9_999_999_999)
    signup_payload = {
        "full_name": f"Signup User {signup_suffix}",
        "phone": str(signup_suffix),
        "email": f"signup_{signup_suffix}@example.com",
        "password": "secret123",
        "role": "student",
    }
    await call("POST", "/api/auth/signup", request_body=signup_payload)
    signup_email = signup_payload["email"]

    # Auth - resend-email-otp (may be rate-limited immediately after signup)
    await call("POST", "/api/auth/resend-email-otp", request_body={"email": signup_email})

    # Auth - verify-email wrong code
    await call("POST", "/api/auth/verify-email", request_body={"email": signup_email, "code": "000000"}, notes="wrong code")

    # Users
    await call("GET", "/api/users/me", headers={"Authorization": f"Bearer {student_token}"})
    await call("PATCH", "/api/users/me", request_body={"full_name": "Updated Student Name"}, headers={"Authorization": f"Bearer {student_token}"})
    await call("GET", "/api/users/me/stats", headers={"Authorization": f"Bearer {student_token}"})

    # Universities
    r = await call("GET", "/api/universities")
    universities = r.json()["data"] if r and r.status_code == 200 else []
    university_id = universities[0]["id"] if universities else None

    # Houses - list
    r = await call("GET", "/api/houses")
    houses = r.json()["data"] if r and r.status_code == 200 and isinstance(r.json().get("data"), list) else []
    house_id = houses[0]["id"] if houses else None

    # Houses - search by university (prefer UNZA since seeded houses are near it)
    unza_id = next((u["id"] for u in universities if u.get("initials") == "UNZA"), university_id)
    if unza_id:
        r = await call("GET", f"/api/houses?university_id={unza_id}&radius_m=10000")
        if r and r.status_code == 200:
            data = r.json().get("data") or {}
            if isinstance(data, dict) and data.get("items"):
                house_id = data["items"][0]["id"]

    # Houses - detail / rooms / similar
    if house_id:
        await call("GET", f"/api/houses/{house_id}")
        await call("GET", f"/api/houses/{house_id}/rooms")
        await call("GET", f"/api/houses/{house_id}/similar")

        if university_id:
            await call("GET", f"/api/houses/{house_id}/eta?university_id={university_id}&mode=DRIVE")

        await call("GET", f"/api/houses/{house_id}/static-map")

    # Houses - nearby
    await call("GET", "/api/houses/nearby?latitude=-15.3918&longitude=28.3296&radius_km=5")

    # Houses - 404
    await call("GET", "/api/houses/nonexistent-id", notes="not found")

    # Images
    image_bytes = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100).getvalue()
    await call("POST", "/api/images/upload", files={"file": ("test.png", image_bytes, "image/png")}, headers={"Authorization": f"Bearer {student_token}"})
    await call("POST", "/api/images/upload", files={"file": ("test.txt", b"not an image", "text/plain")}, headers={"Authorization": f"Bearer {student_token}"}, notes="bad type")

    # Places
    await call("GET", "/api/places/autocomplete?input=Lusaka&session_token=abc123")
    await call("GET", "/api/places/details?place_id=ChIJXXXXXXXX&session_token=abc123")

    # Favorites
    await call("GET", "/api/favorites", headers={"Authorization": f"Bearer {student_token}"})
    if house_id:
        await call("POST", "/api/favorites", request_body={"house_id": house_id}, headers={"Authorization": f"Bearer {student_token}"})
        await call("GET", "/api/favorites", headers={"Authorization": f"Bearer {student_token}"}, notes="after add")
        await call("DELETE", f"/api/favorites/{house_id}", headers={"Authorization": f"Bearer {student_token}"})

    # Bookings - create (need a room_id)
    room_id = None
    if house_id:
        r = await call("GET", f"/api/houses/{house_id}/rooms")
        if r and r.status_code == 200:
            rooms = r.json().get("data") or []
            if rooms:
                room_id = rooms[0]["id"]

    booking_id = None
    if house_id and room_id:
        booking_payload = {
            "house_id": house_id,
            "room_id": room_id,
            "move_in_date": "2026-08-01",
            "note": "Test booking",
        }
        r = await call("POST", "/api/bookings", request_body=booking_payload, headers={"Authorization": f"Bearer {student_token}"})
        if r and r.status_code == 200:
            booking_id = r.json()["data"]["id"]

    await call("GET", "/api/bookings", headers={"Authorization": f"Bearer {student_token}"})

    if booking_id:
        await call("GET", f"/api/bookings/{booking_id}/receipt", headers={"Authorization": f"Bearer {student_token}"})
        await call("PATCH", f"/api/bookings/{booking_id}/status", request_body={"status": "confirmed"}, headers={"Authorization": f"Bearer {landlord_token}"})

    # Payments
    payment_payload = {
        "amount": "150.00",
        "currency": "ZMW",
        "phone": "0977000001",
        "operator": "mtn",
        "country": "zm",
        "booking_id": booking_id,
    }
    r = await call("POST", "/api/payments/lenco/mobile-money", request_body=payment_payload, headers={"Authorization": f"Bearer {student_token}"})
    payment_reference = r.json()["data"]["reference"] if r and r.status_code == 200 else None

    if payment_reference:
        await call("GET", f"/api/payments/lenco/{payment_reference}", headers={"Authorization": f"Bearer {student_token}"})

    card_payload = {
        "amount": "150.00",
        "currency": "ZMW",
        "email": "test@example.com",
        "customer": {"first_name": "Test", "last_name": "User"},
        "billing": {"street_address": "123 Main St", "city": "Lusaka", "state": "Lusaka", "postal_code": "10101", "country": "ZM"},
        "card": {"number": "4111111111111111", "expiry_month": "12", "expiry_year": "2030", "cvv": "123"},
        "redirect_url": "https://example.com/callback",
    }
    await call("POST", "/api/payments/lenco/card", request_body=card_payload, headers={"Authorization": f"Bearer {student_token}"})

    webhook_body = json.dumps({"event": "collection.successful", "data": {"reference": payment_reference or "UNISTAY-xxx", "status": "successful"}})
    await call("POST", "/api/webhooks/lenco", request_body=webhook_body.encode(), headers={"Content-Type": "application/json"})

    # Notifications
    await call("GET", "/api/notifications", headers={"Authorization": f"Bearer {student_token}"})
    await call("PATCH", "/api/notifications/read-all", headers={"Authorization": f"Bearer {student_token}"})

    # Landlords
    await call("GET", "/api/landlords/me/houses", headers={"Authorization": f"Bearer {landlord_token}"})

    house_create_payload = {
        "name": "New Capture House",
        "location": "Lusaka",
        "latitude": -15.3918,
        "longitude": 28.3296,
        "university_id": university_id,
        "price": 2000,
        "walk_time": "10 min",
        "drive_distance": "1.5 km",
        "rating": 4.0,
        "available_spaces": 4,
        "accent": "#FF0000FF",
        "payment_methods": ["mobile_money", "cash"],
        "amenities": ["WiFi"],
        "images": [{"url": "https://example.com/img.jpg", "order": 0}],
        "rooms": [{"type": "Single", "rent": 2000, "deposit": 1000, "available": 2, "features": ["Bed"]}],
    }
    r = await call("POST", "/api/landlords/houses", request_body=house_create_payload, headers={"Authorization": f"Bearer {landlord_token}"})
    new_house_id = r.json()["data"]["id"] if r and r.status_code == 200 else None

    if new_house_id:
        await call("PATCH", f"/api/landlords/houses/{new_house_id}", request_body={"name": "Updated Capture House"}, headers={"Authorization": f"Bearer {landlord_token}"})

        room_payload = {"type": "Double", "rent": 2500, "deposit": 1250, "available": 1, "features": ["Bed", "Desk"]}
        r = await call("POST", f"/api/landlords/houses/{new_house_id}/rooms", request_body=room_payload, headers={"Authorization": f"Bearer {landlord_token}"})
        new_room_id = r.json()["data"]["id"] if r and r.status_code == 200 else None

        if new_room_id:
            await call("PATCH", f"/api/landlords/houses/{new_house_id}/rooms/{new_room_id}", request_body={"rent": 2600}, headers={"Authorization": f"Bearer {landlord_token}"})
            await call("DELETE", f"/api/landlords/houses/{new_house_id}/rooms/{new_room_id}", headers={"Authorization": f"Bearer {landlord_token}"})

        await call("PATCH", f"/api/landlords/houses/{new_house_id}/amenities", request_body={"amenities": ["WiFi", "Parking"]}, headers={"Authorization": f"Bearer {landlord_token}"})

        await call("DELETE", f"/api/landlords/houses/{new_house_id}", headers={"Authorization": f"Bearer {landlord_token}"}, notes="delete house with rooms")

    payment_detail_payload = {
        "bank_name": "Zambia National Bank",
        "account_name": "Test Landlord",
        "account_number": "1234567890",
        "mobile_money_provider": "mtn",
        "mobile_money_number": "0977000001",
        "is_default": True,
    }
    await call("PUT", "/api/landlords/payment-details", request_body=payment_detail_payload, headers={"Authorization": f"Bearer {landlord_token}"})
    await call("GET", "/api/landlords/payment-details", headers={"Authorization": f"Bearer {landlord_token}"})
    await call("GET", "/api/landlords/bookings", headers={"Authorization": f"Bearer {landlord_token}"})

    # Landlords - forbidden for student
    await call("GET", "/api/landlords/me/houses", headers={"Authorization": f"Bearer {student_token}"}, notes="student forbidden")


if __name__ == "__main__":
    asyncio.run(capture())
