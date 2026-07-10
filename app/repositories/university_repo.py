"""University repository for persistence operations."""

from geoalchemy2 import Geometry
from sqlalchemy import func, select

from app.models.university import University
from app.repositories.base import BaseRepository


class UniversityRepository(BaseRepository):
    """Persistence operations for ``University`` records."""

    async def list_all(self) -> list[University]:
        """Return every university with extracted latitude/longitude."""
        result = await self.db.execute(
            select(
                University,
                func.ST_Y(University.coords.cast(Geometry)).label("latitude"),
                func.ST_X(University.coords.cast(Geometry)).label("longitude"),
            ).order_by(University.name)
        )
        universities: list[University] = []
        for row in result.all():
            university = row.University
            university.latitude = row.latitude
            university.longitude = row.longitude
            universities.append(university)
        return universities

    async def get_by_id(self, university_id: str) -> University | None:
        """Return a single university by primary key."""
        result = await self.db.execute(
            select(University).where(University.id == university_id)
        )
        return result.scalar_one_or_none()

    async def create(self, university: University) -> University:
        """Persist a new university and return it."""
        self.db.add(university)
        await self.db.commit()
        await self.db.refresh(university)
        return university
