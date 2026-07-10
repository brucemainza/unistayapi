"""Pydantic schemas for room requests and responses."""

from pydantic import BaseModel, ConfigDict, Field


class RoomResponse(BaseModel):
    """Public room representation within a house."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    rent: int
    deposit: int | None
    available: int
    features: list[str]


class RoomCreateRequest(BaseModel):
    """Request body for creating a room."""

    type: str = Field(..., min_length=1, max_length=50)
    rent: int = Field(..., ge=0)
    deposit: int | None = Field(default=None, ge=0)
    available: int = Field(default=0, ge=0)
    features: list[str] = Field(default_factory=list)


class RoomUpdateRequest(BaseModel):
    """Request body for updating a room."""

    type: str | None = Field(default=None, min_length=1, max_length=50)
    rent: int | None = Field(default=None, ge=0)
    deposit: int | None = Field(default=None, ge=0)
    available: int | None = Field(default=None, ge=0)
    features: list[str] | None = None
