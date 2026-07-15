#!/usr/bin/env python3
"""Verify Google Maps endpoints after billing reactivation."""

import asyncio
import sys
from pathlib import Path

import fakeredis
import httpx
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.models  # noqa: F401
from app.config import settings
from app.dependencies import get_db, get_redis
from app.main import app
from app.models.base import Base
from app.seed import seed_sample_data


async def main():
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

    async def override_get_db():
        async with sessionmaker() as session:
            yield session

    fake_redis = fakeredis.FakeAsyncRedis(decode_responses=True)

    async def override_get_redis():
        yield fake_redis

    prev_env = settings.environment
    settings.environment = "test"
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    results = []
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Get a house and university
            r = await client.get("/api/universities")
            uni_id = r.json()["data"][0]["id"]
            r = await client.get("/api/houses")
            house_id = r.json()["data"][0]["id"]

            # ETA
            url = f"/api/houses/{house_id}/eta?university_id={uni_id}&mode=DRIVE"
            r = await client.get(url)
            print(f"{url} -> {r.status_code}")
            print(r.json() if r.status_code < 300 else r.text)
            print()

            # Autocomplete
            url = "/api/places/autocomplete?input=Lusaka&session_token=abc123"
            r = await client.get(url)
            print(f"{url} -> {r.status_code}")
            auto_body = r.json()
            print(auto_body)
            print()

            # Details with a real place_id from autocomplete
            suggestions = auto_body.get("data", {}).get("suggestions", [])
            real_place_id = suggestions[0].get("place_id") if suggestions else "ChIJSaq8PH3zQBkR6xMgRsGT0NA"
            url = f"/api/places/details?place_id={real_place_id}&session_token=abc123"
            r = await client.get(url)
            print(f"{url} -> {r.status_code}")
            print(r.json() if r.status_code < 300 else r.text)
            print()
    finally:
        app.dependency_overrides.clear()
        settings.environment = prev_env
        await engine.dispose()

    return results


if __name__ == "__main__":
    asyncio.run(main())
