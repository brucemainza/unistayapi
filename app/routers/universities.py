"""Universities router."""

from fastapi import APIRouter, Depends

from app.providers import get_university_service
from app.schemas.common import Envelope, envelope
from app.schemas.university import UniversityResponse
from app.services.university_service import UniversityService

router = APIRouter()


@router.get("", response_model=Envelope[list[UniversityResponse]])
async def list_universities(
    service: UniversityService = Depends(get_university_service),
) -> dict:
    """Return the list of supported universities."""
    universities = await service.list_universities()
    return envelope(True, "Universities retrieved", universities)
