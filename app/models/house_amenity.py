from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class HouseAmenity(Base):
    __tablename__ = "house_amenities"

    house_id: Mapped[str] = mapped_column(
        ForeignKey("houses.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    house: Mapped["House"] = relationship(
        "House", back_populates="amenities", lazy="selectin"
    )
