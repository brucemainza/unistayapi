"""Repository operations for payments."""

from sqlalchemy import select

from app.models.payment import Payment
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository):
    async def create(self, payment: Payment) -> Payment:
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def get_by_reference(self, reference: str) -> Payment | None:
        result = await self.db.execute(
            select(Payment).where(Payment.reference == reference)
        )
        return result.scalar_one_or_none()

    async def update(self, payment: Payment, **kwargs) -> Payment:
        for key, value in kwargs.items():
            if value is not None:
                setattr(payment, key, value)
        await self.db.commit()
        await self.db.refresh(payment)
        return payment
