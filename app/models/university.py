from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class University(Base):
    __tablename__ = "universities"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    initials: Mapped[str] = mapped_column(String(10), nullable=False)
    coords: Mapped[Any] = mapped_column(
        Geography("POINT", srid=4326), nullable=True
    )

    houses: Mapped[list["House"]] = relationship(
        "House", back_populates="university", lazy="selectin"
    )
