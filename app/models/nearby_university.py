from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class NearbyUniversity(Base):
    __tablename__ = "nearby_universities"

    house_id: Mapped[str] = mapped_column(
        ForeignKey("houses.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    distance: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    house: Mapped["House"] = relationship(
        "House", back_populates="nearby_universities", lazy="selectin"
    )
