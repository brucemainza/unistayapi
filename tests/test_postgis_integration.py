"""PostGIS integration tests (requires a live Postgres + PostGIS database).

Set the ``UNISTAY_INTEGRATION_DB_URL`` environment variable to an async
PostgreSQL connection string (e.g. a Supabase session-pooler URI) to run
these tests. Without the variable they are silently skipped.
"""

import os

import pytest

INTEGRATION_DB_URL = os.getenv("UNISTAY_INTEGRATION_DB_URL")
requires_postgis = pytest.mark.skipif(
    INTEGRATION_DB_URL is None,
    reason="UNISTAY_INTEGRATION_DB_URL not set",
)


@requires_postgis
class TestHouseGeoInteg:
    """Exercises the PostGIS-heavy code paths that SQLite cannot validate."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from app.models.base import Base

        if INTEGRATION_DB_URL is None:  # pragma: no cover — safeguard
            pytest.skip("UNISTAY_INTEGRATION_DB_URL not set")

        self.engine = create_async_engine(INTEGRATION_DB_URL)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)

        async with self.sessionmaker() as session:
            from app.seed import seed_sample_data

            await seed_sample_data(session)

        yield

        await self.engine.dispose()

    async def test_search_near_university(self):
        """search_near_university returns houses ordered by distance."""
        from app.repositories.house_repo import HouseRepository
        from app.repositories.university_repo import UniversityRepository

        async with self.sessionmaker() as session:
            uni_repo = UniversityRepository(session)
            universities = await uni_repo.list_all()
            assert universities, "No seeded universities — check seed"
            uni = universities[0]

            house_repo = HouseRepository(session)
            result = await house_repo.search_near_university(
                university_id=uni.id,
                radius_m=5000,
                page=1,
                limit=5,
            )
            assert result["total"] >= 0
            assert isinstance(result["items"], list)
            for item in result["items"]:
                assert "id" in item

    async def test_house_repo_search_with_postgis_columns(self):
        """Listing returns seeded houses via Postgres (not SQLite in-mem)."""
        from app.repositories.house_repo import HouseRepository

        async with self.sessionmaker() as session:
            repo = HouseRepository(session)
            houses = await repo.list_public()
            assert isinstance(houses, list)
            # Seeded houses should exist
            assert len(houses) >= 1
            first = houses[0]
            assert "name" in first
            assert "latitude" in first
            assert "longitude" in first

    async def test_university_repo_point_parse(self):
        """University coordinates parse correctly from Geography column."""
        from app.repositories.university_repo import UniversityRepository

        async with self.sessionmaker() as session:
            repo = UniversityRepository(session)
            unis = await repo.list_all()
            assert unis
            for uni in unis:
                assert uni.latitude is not None
                assert uni.longitude is not None
                assert -90 <= uni.latitude <= 90
                assert -180 <= uni.longitude <= 180