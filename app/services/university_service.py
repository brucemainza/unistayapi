"""University business logic."""

from app.models.university import University
from app.repositories.university_repo import UniversityRepository
from app.schemas.university import UniversityResponse


class UniversityService:
    """High-level service for university listings."""

    def __init__(self, repo: UniversityRepository) -> None:
        self.repo = repo

    async def list_universities(self) -> list[dict]:
        """Return all universities as serialisable dictionaries."""
        universities = await self.repo.list_all()
        return [self._to_dict(u) for u in universities]

    def _to_dict(self, university: University) -> dict:
        return UniversityResponse(
            id=university.id,
            name=university.name,
            initials=university.initials,
            latitude=float(university.latitude)
            if university.latitude is not None
            else None,
            longitude=float(university.longitude)
            if university.longitude is not None
            else None,
        ).model_dump()
