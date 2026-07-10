"""Small geospatial helpers shared by seed data and repositories."""

from math import asin, cos, radians, sin, sqrt
from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession


def get_dialect_name(db: AsyncSession) -> str:
    bind = db.get_bind()
    return bind.dialect.name if bind is not None else ""


def point_wkt(latitude: float, longitude: float) -> str:
    return f"POINT({longitude} {latitude})"


def point_value(db: AsyncSession, latitude: float, longitude: float) -> Any:
    wkt = point_wkt(latitude, longitude)
    if get_dialect_name(db) == "postgresql":
        return func.ST_GeogFromText(wkt)
    return wkt


def parse_point(value: Any) -> tuple[float | None, float | None]:
    if value is None:
        return None, None

    text = str(value)
    if not text.startswith("POINT(") or not text.endswith(")"):
        return None, None

    try:
        longitude_text, latitude_text = text[6:-1].split()
        return float(latitude_text), float(longitude_text)
    except (TypeError, ValueError):
        return None, None


def distance_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    radius_km = 6371.0
    d_lat = radians(latitude_b - latitude_a)
    d_lon = radians(longitude_b - longitude_a)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(latitude_a))
        * cos(radians(latitude_b))
        * sin(d_lon / 2) ** 2
    )
    return 2 * radius_km * asin(sqrt(a))
