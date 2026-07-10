"""Universities router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.repositories.university_repo import UniversityRepository
from app.schemas.common import envelope
from app.services.university_service import UniversityService

router = APIRouter()


@router.get("")
async def list_universities(db: AsyncSession = Depends(get_db)) -> dict:
    """Return the list of supported universities."""
    service = UniversityService(UniversityRepository(db))
    universities = await service.list_universities()
    return envelope(True, "Universities retrieved", universities)
