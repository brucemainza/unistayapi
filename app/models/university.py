from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db_types import GeoPoint
from app.models.base import Base


class University(Base):
    __tablename__ = "universities"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    initials: Mapped[str] = mapped_column(String(10), nullable=False)
    coords: Mapped[str | None] = mapped_column(GeoPoint(), nullable=True)

    houses: Mapped[list["House"]] = relationship(
        "House", back_populates="university", lazy="selectin"
    )
