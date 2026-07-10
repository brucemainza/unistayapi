"""Schemas for booking requests and responses."""

from datetime import date

from pydantic import BaseModel, Field


class BookingCreateRequest(BaseModel):
    house_id: str
    room_id: str
    move_in_date: date
    note: str | None = Field(default=None, max_length=500)


class BookingStatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern=r"^(pending|confirmed|rejected|cancelled)$")


class BookingResponse(BaseModel):
    id: str
    studentId: str
    houseId: str
    roomId: str
    moveInDate: str
    status: str
    note: str | None
    houseName: str | None = None
    roomType: str | None = None
    createdAt: str
    updatedAt: str
