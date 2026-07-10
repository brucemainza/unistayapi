"""Repository operations for landlord settlement details."""

from sqlalchemy import select

from app.models.landlord_payment_detail import LandlordPaymentDetail
from app.repositories.base import BaseRepository


class LandlordPaymentDetailRepository(BaseRepository):
    async def get_by_landlord(self, landlord_id: str) -> LandlordPaymentDetail | None:
        result = await self.db.execute(
            select(LandlordPaymentDetail).where(
                LandlordPaymentDetail.landlord_id == landlord_id
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self, landlord_id: str, values: dict
    ) -> LandlordPaymentDetail:
        detail = await self.get_by_landlord(landlord_id)
        if detail is None:
            detail = LandlordPaymentDetail(landlord_id=landlord_id, **values)
            self.db.add(detail)
        else:
            for key, value in values.items():
                setattr(detail, key, value)
        await self.db.commit()
        await self.db.refresh(detail)
        return detail
