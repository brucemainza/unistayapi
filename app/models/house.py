from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db_types import GeoPoint
from app.models.base import Base


class House(Base):
    __tablename__ = "houses"
    __table_args__ = (
        Index("idx_houses_coords", "coords", postgresql_using="gist"),
    )

    landlord_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    coords: Mapped[str] = mapped_column(GeoPoint(), nullable=False)
    formatted_address: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    is_deleted: Mapped[bool] = mapped_column(
        default=False, nullable=False, index=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False
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
