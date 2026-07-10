"""Database types that keep production PostGIS and tests portable."""

from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import String
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator


class GeoPoint(TypeDecorator):
    """Use PostGIS geography in Postgres and WKT text in lightweight tests."""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Geography("POINT", srid=4326))
        return dialect.type_descriptor(String(255))
