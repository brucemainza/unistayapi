"""House repository for persistence and search operations."""

from geoalchemy2 import Geography, Geometry
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.geo import point_wkt
from app.models.house import House
from app.models.house_amenity import HouseAmenity
from app.models.university import University
from app.repositories.base import BaseRepository


class HouseRepository(BaseRepository):
    """Persistence and search operations for ``House`` records."""

    async def search(
        self,
        *,
        university: str | None = None,
        q: str | None = None,
        amenities: list[str] | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[House], int]:
        """Return filtered, paginated houses plus total count."""
        stmt = (
            select(House)
            .options(
                selectinload(House.landlord),
                selectinload(House.university),
                selectinload(House.amenities),
                selectinload(House.images),
                selectinload(House.nearby_universities),
                selectinload(House.rooms),
            )
            .order_by(House.created_at.desc())
        )

        if university:
            stmt = stmt.join(University).where(
                (University.id == university) | (University.initials == university)
            )

        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(
                (House.name.ilike(pattern)) | (House.location.ilike(pattern))
            )

        if min_price is not None:
            stmt = stmt.where(House.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(House.price <= max_price)

        if amenities:
            amenity_subq = (
                select(HouseAmenity.house_id)
                .where(HouseAmenity.name.in_(amenities))
                .group_by(HouseAmenity.house_id)
                .having(func.count(HouseAmenity.name) == len(amenities))
            )
            stmt = stmt.where(House.id.in_(amenity_subq))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_id(self, house_id: str) -> House | None:
        """Return a single house with all related data loaded."""
        result = await self.db.execute(
            select(House)
            .where(House.id == house_id)
            .options(
                selectinload(House.landlord),
                selectinload(House.university),
                selectinload(House.amenities),
                selectinload(House.images),
                selectinload(House.nearby_universities),
                selectinload(House.rooms),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_landlord(self, landlord_id: str) -> list[House]:
        """Return all houses owned by a landlord."""
        result = await self.db.execute(
            select(House)
            .where(House.landlord_id == landlord_id)
            .options(
                selectinload(House.landlord),
                selectinload(House.university),
                selectinload(House.amenities),
                selectinload(House.images),
                selectinload(House.nearby_universities),
                selectinload(House.rooms),
            )
            .order_by(House.created_at.desc())
        )
        return list(result.scalars().all())

    async def nearby(
        self, latitude: float, longitude: float, radius_km: float = 10
    ) -> list[House]:
        """Return houses within ``radius_km`` of the given coordinate."""
        from app.geo import distance_km, get_dialect_name, parse_point

        if get_dialect_name(self.db) != "postgresql":
            result = await self.db.execute(
                select(House).options(
                    selectinload(House.landlord),
                    selectinload(House.university),
                    selectinload(House.amenities),
                    selectinload(House.images),
                    selectinload(House.nearby_universities),
                    selectinload(House.rooms),
                )
            )
            houses = list(result.scalars().all())
            nearby_houses: list[tuple[float, House]] = []
            for house in houses:
                lat, lon = parse_point(house.coords)
                if lat is None or lon is None:
                    continue
                dist = distance_km(latitude, longitude, lat, lon)
                if dist <= radius_km:
                    nearby_houses.append((dist, house))
            nearby_houses.sort(key=lambda item: item[0])
            return [house for _, house in nearby_houses[:20]]

        point = func.ST_GeogFromText(point_wkt(latitude, longitude))
        result = await self.db.execute(
            select(House)
            .where(
                func.ST_DWithin(House.coords, point, radius_km * 1000)
            )
            .options(
                selectinload(House.landlord),
                selectinload(House.university),
                selectinload(House.amenities),
                selectinload(House.images),
                selectinload(House.nearby_universities),
                selectinload(House.rooms),
            )
            .order_by(func.ST_Distance(House.coords, point))
            .limit(20)
        )
        return list(result.scalars().all())

    async def create(self, house: House) -> House:
        """Persist a new house and return it."""
        self.db.add(house)
        await self.db.commit()
        await self.db.refresh(house)
        return house
