"""Bookings router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_db
from app.repositories.booking_repo import BookingRepository
from app.repositories.house_repo import HouseRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.room_repo import RoomRepository
from app.schemas.booking import BookingCreateRequest, BookingStatusUpdateRequest
from app.schemas.common import envelope
from app.services.booking_service import BookingService

router = APIRouter()


def _service(db: AsyncSession) -> BookingService:
    return BookingService(
        BookingRepository(db),
        HouseRepository(db),
        RoomRepository(db),
        NotificationRepository(db),
    )


@router.post("")
async def create_booking(
    body: BookingCreateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    booking = await _service(db).create_booking(current_user.id, body)
    return envelope(True, "Booking created", booking)


@router.get("")
async def list_bookings(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict:
    bookings = await _service(db).list_bookings(current_user.id)
    return envelope(True, "Bookings retrieved", bookings)


@router.get("/{booking_id}/receipt")
async def booking_receipt(
    booking_id: str, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict:
    receipt = await _service(db).get_receipt(current_user.id, booking_id)
    return envelope(True, "Booking receipt", receipt)


@router.patch("/{booking_id}/status")
async def update_booking_status(
    booking_id: str,
    body: BookingStatusUpdateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    booking = await _service(db).update_status(
        booking_id, body.status, actor_id=current_user.id
    )
    return envelope(True, "Booking status updated", booking)
