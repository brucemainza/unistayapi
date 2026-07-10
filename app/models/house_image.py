from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class HouseImage(Base):
    __tablename__ = "house_images"

    house_id: Mapped[str] = mapped_column(
        ForeignKey("houses.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    house: Mapped["House"] = relationship(
        "House", back_populates="images", lazy="selectin"
    )
