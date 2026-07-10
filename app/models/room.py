from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Room(Base):
    __tablename__ = "rooms"

    house_id: Mapped[str] = mapped_column(ForeignKey("houses.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    rent: Mapped[int] = mapped_column(Integer, nullable=False)
    deposit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    features: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
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

    house: Mapped["House"] = relationship(
        "House", back_populates="rooms", lazy="selectin"
    )
