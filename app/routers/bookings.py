"""Bookings router."""

from fastapi import APIRouter, Depends, Response

from app.dependencies import StudentUser
from app.providers import get_booking_service
from app.schemas.booking import BookingCreateRequest, BookingStatusUpdateRequest
from app.schemas.common import envelope
from app.services.booking_service import BookingService

router = APIRouter()


@router.post("")
async def create_booking(
    body: BookingCreateRequest,
    current_user: StudentUser,
    service: BookingService = Depends(get_booking_service),
) -> dict:
    booking = await service.create_booking(current_user.id, body)
    return envelope(True, "Booking created", booking)


@router.get("")
async def list_bookings(
    current_user: StudentUser,
    service: BookingService = Depends(get_booking_service),
) -> dict:
    bookings = await service.list_bookings(current_user.id)
    return envelope(True, "Bookings retrieved", bookings)


@router.get("/{booking_id}/receipt")
async def booking_receipt(
    booking_id: str,
    current_user: StudentUser,
    service: BookingService = Depends(get_booking_service),
) -> dict:
    receipt = await service.get_receipt(current_user.id, booking_id)
    return envelope(True, "Booking receipt", receipt)


@router.get("/{booking_id}/receipt.pdf")
async def booking_receipt_pdf(
    booking_id: str,
    current_user: StudentUser,
    service: BookingService = Depends(get_booking_service),
) -> Response:
    filename, pdf_bytes = await service.get_receipt_pdf(current_user.id, booking_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{booking_id}/receipt/email")
async def email_booking_receipt(
    booking_id: str,
    current_user: StudentUser,
    service: BookingService = Depends(get_booking_service),
) -> dict:
    result = await service.email_receipt(current_user.id, booking_id)
    return envelope(True, "Booking receipt emailed", result)


@router.patch("/{booking_id}/status")
async def update_booking_status(
    booking_id: str,
    body: BookingStatusUpdateRequest,
    current_user: StudentUser,
    service: BookingService = Depends(get_booking_service),
) -> dict:
    booking = await service.update_status(
        booking_id, body.status, actor_id=current_user.id
    )
    return envelope(True, "Booking status updated", booking)
