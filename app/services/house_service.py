"""House business logic."""

from sqlalchemy import delete

from app.exceptions import NotFoundError
from app.geo import point_value
from app.models.house import House
from app.models.house_amenity import HouseAmenity
from app.models.house_image import HouseImage
from app.models.nearby_university import NearbyUniversity
from app.models.room import Room
from app.repositories.house_repo import HouseRepository
from app.repositories.room_repo import RoomRepository
from app.schemas.house import (
    HouseCreateRequest,
    HouseUpdateRequest,
)
from app.services.serializers import house_to_dict, room_to_dict


class HouseService:
    """High-level service for house listings, details, and landlord management."""

    def __init__(
        self,
        house_repo: HouseRepository,
        room_repo: RoomRepository | None = None,
    ) -> None:
        self.house_repo = house_repo
        self.room_repo = room_repo

    async def list_houses(
        self,
        *,
        university: str | None = None,
        q: str | None = None,
        amenities: list[str] | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[dict]:
        """Return a list of houses matching the filters."""
        houses, _ = await self.house_repo.search(
            university=university,
            q=q,
            amenities=amenities,
            min_price=min_price,
            max_price=max_price,
            page=page,
            limit=limit,
        )
        return [house_to_dict(house) for house in houses]

    async def get_house(self, house_id: str) -> dict:
        """Return detailed information for a single house."""
        house = await self.house_repo.get_by_id(house_id)
        if house is None:
            raise NotFoundError("House not found")
        return house_to_dict(house)

    async def list_rooms(self, house_id: str) -> list[dict]:
        """Return all rooms for a house."""
        if self.room_repo is None:
            raise NotFoundError("Room repository not available")
        house = await self.house_repo.get_by_id(house_id)
        if house is None:
            raise NotFoundError("House not found")
        rooms = await self.room_repo.get_by_house_id(house_id)
        return [room_to_dict(room) for room in rooms]

    async def get_similar(self, house_id: str) -> list[dict]:
        """Return houses similar to the given house (same university or location)."""
        house = await self.house_repo.get_by_id(house_id)
        if house is None:
            raise NotFoundError("House not found")
        filters: dict = {"limit": 6}
        if house.university_id:
            filters["university"] = house.university_id
        else:
            filters["q"] = house.location
        houses, _ = await self.house_repo.search(**filters)
        return [
            house_to_dict(h)
            for h in houses
            if h.id != house_id
        ][:5]

    async def get_nearby(
        self, latitude: float, longitude: float, radius_km: float = 10
    ) -> list[dict]:
        """Return houses within a radius of a coordinate using PostGIS."""
        houses = await self.house_repo.nearby(latitude, longitude, radius_km)
        return [house_to_dict(house) for house in houses]

    async def list_by_landlord(self, landlord_id: str) -> list[dict]:
        """Return all houses owned by a landlord."""
        houses = await self.house_repo.list_by_landlord(landlord_id)
        return [house_to_dict(house) for house in houses]

    async def create_house(self, landlord_id: str, request: HouseCreateRequest) -> dict:
        """Create a new house with amenities, images, nearby universities and rooms."""
        coords = None
        if request.latitude is not None and request.longitude is not None:
            coords = point_value(self.house_repo.db, request.latitude, request.longitude)

        house = House(
            landlord_id=landlord_id,
            name=request.name,
            location=request.location,
            coords=coords,
            university_id=request.university_id,
            price=request.price,
            walk_time=request.walk_time,
            drive_distance=request.drive_distance,
            rating=request.rating,
            available_spaces=request.available_spaces,
            accent=request.accent,
            payment_methods=request.payment_methods,
        )
        house.amenities = [HouseAmenity(name=name) for name in request.amenities]
        house.images = [
            HouseImage(url=url, order=index)
            for index, url in enumerate(request.image_urls)
        ]
        house.nearby_universities = [
            NearbyUniversity(name=nu.name, distance=nu.distance)
            for nu in request.nearby_universities
        ]

        house = await self.house_repo.create(house)

        if self.room_repo is not None:
            for room_data in request.rooms:
                room = Room(
                    house_id=house.id,
                    type=room_data.get("type", "Room"),
                    rent=room_data.get("rent", 0),
                    deposit=room_data.get("deposit"),
                    available=room_data.get("available", 0),
                    features=room_data.get("features", []),
                )
                self.room_repo.db.add(room)
            await self.room_repo.db.commit()

        return await self.get_house(house.id)

    async def update_house(
        self, house_id: str, request: HouseUpdateRequest
    ) -> dict:
        """Update editable house fields."""
        house = await self.house_repo.get_by_id(house_id)
        if house is None:
            raise NotFoundError("House not found")

        update_data = request.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(house, key, value)

        await self.house_repo.db.commit()
        await self.house_repo.db.refresh(house)
        return house_to_dict(house)

    async def delete_house(self, house_id: str) -> None:
        """Delete a house and its related records (cascade)."""
        house = await self.house_repo.get_by_id(house_id)
        if house is None:
            raise NotFoundError("House not found")
        await self.house_repo.db.delete(house)
        await self.house_repo.db.commit()

    async def update_amenities(self, house_id: str, amenities: list[str]) -> dict:
        """Replace the amenities list for a house."""
        house = await self.house_repo.get_by_id(house_id)
        if house is None:
            raise NotFoundError("House not found")

        await self.house_repo.db.execute(
            delete(HouseAmenity).where(HouseAmenity.house_id == house_id)
        )
        house.amenities = [HouseAmenity(name=name) for name in amenities]
        await self.house_repo.db.commit()
        await self.house_repo.db.refresh(house)
        return house_to_dict(house)
