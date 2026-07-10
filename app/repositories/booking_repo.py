"""Repository operations for bookings."""

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.exceptions import ConflictError, NotFoundError
from app.models.booking import Booking
from app.models.house import House
from app.models.room import Room
from app.repositories.base import BaseRepository


BOOKING_LOAD_OPTIONS = (
    selectinload(Booking.house),
    selectinload(Booking.room),
    selectinload(Booking.student),
)


class BookingRepository(BaseRepository):
    async def get_by_id(self, booking_id: str) -> Booking | None:
        result = await self.db.execute(
            select(Booking).options(*BOOKING_LOAD_OPTIONS).where(Booking.id == booking_id)
        )
        return result.scalar_one_or_none()

    async def list_by_student(self, student_id: str) -> list[Booking]:
        result = await self.db.execute(
            select(Booking)
            .options(*BOOKING_LOAD_OPTIONS)
            .where(Booking.student_id == student_id)
            .order_by(Booking.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_landlord(self, landlord_id: str) -> list[Booking]:
        result = await self.db.execute(
            select(Booking)
            .join(House, Booking.house_id == House.id)
            .options(*BOOKING_LOAD_OPTIONS)
            .where(House.landlord_id == landlord_id)
            .order_by(Booking.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, booking: Booking) -> Booking:
        room_result = await self.db.execute(
            select(Room).where(Room.id == booking.room_id).with_for_update()
        )
        room = room_result.scalar_one_or_none()
        if room is None:
            raise NotFoundError("Room not found")

        active_count = await self.db.scalar(
            select(func.count(Booking.id)).where(
                Booking.room_id == booking.room_id,
                Booking.status.in_(("pending", "confirmed")),
            )
        )
        if int(active_count or 0) >= room.available:
            raise ConflictError("Room no longer available")

        self.db.add(booking)
        await self.db.commit()
        return await self.get_by_id(booking.id) or booking

    async def update_status(self, booking: Booking, status: str) -> Booking:
        booking.status = status
        await self.db.commit()
        return await self.get_by_id(booking.id) or booking

    async def latest_active_by_student(self, student_id: str) -> Booking | None:
        result = await self.db.execute(
            select(Booking)
            .options(*BOOKING_LOAD_OPTIONS)
            .where(
                Booking.student_id == student_id,
                Booking.status.in_(("pending", "confirmed")),
            )
            .order_by(Booking.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
