"""Shared pytest fixtures with an isolated async SQLite database."""

import random
from collections.abc import AsyncGenerator, Callable

import fakeredis
import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register SQLAlchemy models
from app.config import settings
from app.dependencies import get_db, get_redis
from app.main import app
from app.models.base import Base
from app.seed import seed_sample_data


@pytest_asyncio.fixture
async def db_sessionmaker() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
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

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with sessionmaker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    previous_env = settings.environment
    previous_mock = settings.lenco_mock
    settings.environment = "test"
    settings.lenco_mock = True
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield sessionmaker
    finally:
        app.dependency_overrides.clear()
        settings.environment = previous_env
        settings.lenco_mock = previous_mock
        await engine.dispose()


@pytest_asyncio.fixture
def fake_redis():
    return fakeredis.FakeAsyncRedis(decode_responses=True)


@pytest_asyncio.fixture
async def client(db_sessionmaker, fake_redis):
    async def override_get_redis() -> AsyncGenerator[fakeredis.FakeAsyncRedis, None]:
        yield fake_redis

    app.dependency_overrides[get_redis] = override_get_redis
    transport = ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_redis, None)


@pytest.fixture
def unique_user_payload() -> Callable[[str], dict]:
    def build(role: str = "student") -> dict:
        suffix = random.randint(1_000_000_000, 9_999_999_999)
        return {
            "full_name": f"Test {role.title()}",
            "phone": str(suffix),
            "email": f"test_{role}_{suffix}@example.com",
            "password": "secret123",
            "role": role,
        }

    return build


async def register_user(client: httpx.AsyncClient, payload: dict | None = None) -> dict:
    if payload is None:
        suffix = random.randint(1_000_000_000, 9_999_999_999)
        payload = {
            "full_name": "Test User",
            "phone": str(suffix),
            "email": f"test_{suffix}@example.com",
            "password": "secret123",
            "role": "student",
        }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["data"]
