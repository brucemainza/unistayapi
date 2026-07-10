from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Booking(Base):
    __tablename__ = "bookings"

    student_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    house_id: Mapped[str] = mapped_column(
        ForeignKey("houses.id"), nullable=False
    )
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id"), nullable=False)
    move_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
