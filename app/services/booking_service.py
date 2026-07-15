"""Business logic for booking requests."""

from app.exceptions import AuthError, NotFoundError, ValidationError
from app.models.booking import Booking
from app.models.notification import Notification
from app.repositories.booking_repo import BookingRepository
from app.repositories.house_repo import HouseRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.room_repo import RoomRepository
from app.schemas.booking import BookingCreateRequest
from app.services.email import send_booking_receipt_email
from app.services.receipt import (
    build_receipt_payload,
    receipt_filename,
    render_receipt_pdf,
)
from app.services.serializers import booking_to_dict


class BookingService:
    def __init__(
        self,
        booking_repo: BookingRepository,
        house_repo: HouseRepository,
        room_repo: RoomRepository,
        notification_repo: NotificationRepository | None = None,
        payment_repo: PaymentRepository | None = None,
    ) -> None:
        self.booking_repo = booking_repo
        self.house_repo = house_repo
        self.room_repo = room_repo
        self.notification_repo = notification_repo
        self.payment_repo = payment_repo

    async def create_booking(self, student_id: str, request: BookingCreateRequest) -> dict:
        house = await self.house_repo.get_by_id(request.house_id)
        if house is None:
            raise NotFoundError("House not found")
        room = await self.room_repo.get_by_id(request.room_id)
        if room is None or room.house_id != house.id:
            raise NotFoundError("Room not found")

        booking = Booking(
            student_id=student_id,
            house_id=house.id,
            room_id=room.id,
            move_in_date=request.move_in_date,
            note=request.note,
        )
        booking = await self.booking_repo.create(booking)
        if self.notification_repo is not None:
            await self.notification_repo.create(
                Notification(
                    user_id=house.landlord_id,
                    title="New booking request",
                    body=f"{house.name} has a new booking request.",
                )
            )
        return booking_to_dict(booking)

    async def list_bookings(self, student_id: str) -> list[dict]:
        bookings = await self.booking_repo.list_by_student(student_id)
        return [booking_to_dict(booking) for booking in bookings]

    async def get_receipt(self, student_id: str, booking_id: str) -> dict:
        booking = await self._get_student_booking(student_id, booking_id)
        return await self._receipt_payload(booking)

    async def get_receipt_pdf(self, student_id: str, booking_id: str) -> tuple[str, bytes]:
        receipt = await self.get_receipt(student_id, booking_id)
        filename = receipt_filename(booking_id)
        return filename, render_receipt_pdf(receipt)

    async def email_receipt(self, student_id: str, booking_id: str) -> dict:
        booking = await self._get_student_booking(student_id, booking_id)
        payment = await self._successful_payment_for_booking(booking.id)
        receipt = build_receipt_payload(booking, payment)
        filename = receipt_filename(booking_id)
        pdf_bytes = render_receipt_pdf(receipt)
        sent = await send_booking_receipt_email(
            booking.student.email, pdf_bytes=pdf_bytes, filename=filename
        )
        if not sent:
            raise ValidationError("Receipt email could not be sent")
        return {"email": booking.student.email, "filename": filename}

    async def _get_student_booking(self, student_id: str, booking_id: str) -> Booking:
        booking = await self.booking_repo.get_by_id(booking_id)
        if booking is None:
            raise NotFoundError("Booking not found")
        if booking.student_id != student_id:
            raise AuthError("Booking access denied")
        return booking

    async def _receipt_payload(self, booking: Booking) -> dict:
        payment = None
        if self.payment_repo is not None:
            payment = await self.payment_repo.latest_by_booking_id(booking.id)
        return build_receipt_payload(booking, payment)

    async def _successful_payment_for_booking(self, booking_id: str):
        if self.payment_repo is None:
            raise ValidationError("Payment is required before sending a receipt")
        payment = await self.payment_repo.latest_by_booking_id(booking_id)
        if payment is None or payment.status not in {"successful", "completed"}:
            raise ValidationError("Receipt can only be emailed after payment succeeds")
        return payment

    async def update_status(
        self,
        booking_id: str,
        status: str,
        *,
        actor_id: str,
        landlord_only: bool = False,
    ) -> dict:
        booking = await self.booking_repo.get_by_id(booking_id)
        if booking is None:
            raise NotFoundError("Booking not found")
        if landlord_only and (booking.house is None or booking.house.landlord_id != actor_id):
            raise AuthError("Booking access denied")
        if not landlord_only and booking.student_id != actor_id:
            raise AuthError("Booking access denied")
        booking = await self.booking_repo.update_status(booking, status)
        if self.notification_repo is not None:
            await self.notification_repo.create(
                Notification(
                    user_id=booking.student_id,
                    title="Booking status updated",
                    body=f"Your booking is now {status}.",
                )
            )
        return booking_to_dict(booking)
