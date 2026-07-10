"""Pydantic schemas for university responses."""

from pydantic import BaseModel, ConfigDict


class UniversityResponse(BaseModel):
    """Public university representation with coordinates."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    initials: str
    latitude: float | None
    longitude: float | None
