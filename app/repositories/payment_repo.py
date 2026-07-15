"""Repository operations for payments."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.booking import Booking
from app.models.house import House
from app.models.payment import Payment
from app.repositories.base import BaseRepository


PAYMENT_LOAD_OPTIONS = (
    selectinload(Payment.booking).selectinload(Booking.student),
    selectinload(Payment.booking)
    .selectinload(Booking.house)
    .selectinload(House.university),
    selectinload(Payment.booking)
    .selectinload(Booking.house)
    .selectinload(House.amenities),
    selectinload(Payment.booking)
    .selectinload(Booking.house)
    .selectinload(House.images),
    selectinload(Payment.booking)
    .selectinload(Booking.house)
    .selectinload(House.nearby_universities),
    selectinload(Payment.booking).selectinload(Booking.room),
)


class PaymentRepository(BaseRepository):
    async def create(self, payment: Payment) -> Payment:
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def add(self, payment: Payment) -> Payment:
        """Stage a new payment without committing (unit-of-work friendly)."""
        self.db.add(payment)
        await self.db.flush()
        return payment

    async def get_by_reference(self, reference: str) -> Payment | None:
        result = await self.db.execute(
            select(Payment)
            .options(*PAYMENT_LOAD_OPTIONS)
            .where(Payment.reference == reference)
        )
        return result.scalar_one_or_none()

    async def latest_by_booking_id(self, booking_id: str) -> Payment | None:
        result = await self.db.execute(
            select(Payment)
            .options(*PAYMENT_LOAD_OPTIONS)
            .where(Payment.booking_id == booking_id)
            .order_by(Payment.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update(self, payment: Payment, **kwargs) -> Payment:
        for key, value in kwargs.items():
            if value is not None:
                setattr(payment, key, value)
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def apply(self, payment: Payment, **kwargs) -> Payment:
        """Apply field updates without committing (unit-of-work friendly)."""
        for key, value in kwargs.items():
            if value is not None:
                setattr(payment, key, value)
        await self.db.flush()
        return payment

    async def commit_and_refresh(self, payment: Payment) -> Payment:
        """Commit the current transaction and refresh the payment instance."""
        await self.db.commit()
        await self.db.refresh(payment)
        return payment
