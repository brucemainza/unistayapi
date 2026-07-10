from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LandlordPaymentDetail(Base):
    __tablename__ = "landlord_payment_details"

    landlord_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False, unique=True
    )
    bank_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mobile_money_provider: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    mobile_money_number: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )
