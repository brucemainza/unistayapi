#!/usr/bin/env python3
"""Verify the app's /api/images/upload endpoint with a real valid PNG."""

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

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Register a student
            r = await client.post("/api/auth/register", json={
                "full_name": "Upload Test",
                "phone": "0000000001",
                "email": "upload@test.com",
                "password": "secret123",
                "role": "student",
            })
            token = r.json()["data"]["token"]

            png_path = Path(__file__).parent / "test_image.png"
            files = {"file": ("test.png", png_path.read_bytes(), "image/png")}
            r = await client.post("/api/images/upload", files=files, headers={"Authorization": f"Bearer {token}"})
            print(f"/api/images/upload -> {r.status_code}")
            print(r.json() if r.status_code < 300 else r.text)
    finally:
        app.dependency_overrides.clear()
        settings.environment = prev_env
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
