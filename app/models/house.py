from datetime import datetime
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class House(Base):
    __tablename__ = "houses"

    landlord_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    coords: Mapped[Any] = mapped_column(
        Geography("POINT", srid=4326), nullable=True
    )
    university_id: Mapped[str | None] = mapped_column(
        ForeignKey("universities.id"), nullable=True
    )
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    walk_time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    drive_distance: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    available_spaces: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    accent: Mapped[str] = mapped_column(
        String(9), nullable=False, default="#FFFF8C00"
    )
    payment_methods: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    landlord: Mapped["User"] = relationship(
        "User", back_populates="houses", lazy="selectin"
    )
    university: Mapped["University | None"] = relationship(
        "University", back_populates="houses", lazy="selectin"
    )
    rooms: Mapped[list["Room"]] = relationship(
        "Room", back_populates="house", lazy="selectin"
    )
    amenities: Mapped[list["HouseAmenity"]] = relationship(
        "HouseAmenity",
        back_populates="house",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    images: Mapped[list["HouseImage"]] = relationship(
        "HouseImage",
        back_populates="house",
        lazy="selectin",
        order_by="HouseImage.order",
        cascade="all, delete-orphan",
    )
    nearby_universities: Mapped[list["NearbyUniversity"]] = relationship(
        "NearbyUniversity",
        back_populates="house",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
