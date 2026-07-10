from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EtaCache(Base):
    __tablename__ = "eta_cache"

    house_id: Mapped[str] = mapped_column(
        ForeignKey("houses.id"), nullable=False
    )
    university_id: Mapped[str] = mapped_column(
        ForeignKey("universities.id"), nullable=False
    )
    mode: Mapped[str] = mapped_column(String(10), nullable=False)
    duration_s: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_m: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False
    )

    house: Mapped["House"] = relationship("House", lazy="selectin")
    university: Mapped["University"] = relationship("University", lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "house_id", "university_id", "mode", name="uix_eta_cache"
        ),
    )
