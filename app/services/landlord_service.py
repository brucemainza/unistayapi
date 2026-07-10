"""Business logic for landlord management workflows."""

from app.exceptions import AuthError, NotFoundError
from app.models.room import Room
from app.repositories.booking_repo import BookingRepository
from app.repositories.house_repo import HouseRepository
from app.repositories.landlord_payment_detail_repo import LandlordPaymentDetailRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.room_repo import RoomRepository
from app.schemas.booking import BookingStatusUpdateRequest
from app.schemas.house import AmenitiesUpdateRequest, HouseCreateRequest, HouseUpdateRequest
from app.schemas.landlord import LandlordPaymentDetailRequest
from app.schemas.room import RoomCreateRequest, RoomUpdateRequest
from app.services.booking_service import BookingService
from app.services.house_service import HouseService
from app.services.serializers import (
    booking_to_dict,
    house_to_dict,
    landlord_payment_detail_to_dict,
    room_to_dict,
)


class LandlordService:
    def __init__(
        self,
        house_repo: HouseRepository,
        room_repo: RoomRepository,
        booking_repo: BookingRepository,
        payment_detail_repo: LandlordPaymentDetailRepository,
        notification_repo: NotificationRepository | None = None,
    ) -> None:
        self.house_repo = house_repo
        self.room_repo = room_repo
        self.booking_repo = booking_repo
        self.payment_detail_repo = payment_detail_repo
        self.notification_repo = notification_repo

    async def list_houses(self, landlord_id: str) -> list[dict]:
        houses = await self.house_repo.list_by_landlord(landlord_id)
        return [house_to_dict(house) for house in houses]

    async def create_house(self, landlord_id: str, request: HouseCreateRequest) -> dict:
        return await HouseService(self.house_repo, self.room_repo).create_house(
            landlord_id, request
        )

    async def update_house(
        self, landlord_id: str, house_id: str, request: HouseUpdateRequest
    ) -> dict:
        await self._require_house_owner(landlord_id, house_id)
        return await HouseService(self.house_repo, self.room_repo).update_house(
            house_id, request
        )

    async def delete_house(self, landlord_id: str, house_id: str) -> None:
        await self._require_house_owner(landlord_id, house_id)
        await HouseService(self.house_repo, self.room_repo).delete_house(house_id)

    async def add_room(
        self, landlord_id: str, house_id: str, request: RoomCreateRequest
    ) -> dict:
        await self._require_house_owner(landlord_id, house_id)
        room = Room(
            house_id=house_id,
            type=request.type,
            rent=request.rent,
            deposit=request.deposit,
            available=request.available,
            features=request.features,
        )
        room = await self.room_repo.create(room)
        return room_to_dict(room)

    async def update_room(
        self,
        landlord_id: str,
        house_id: str,
        room_id: str,
        request: RoomUpdateRequest,
    ) -> dict:
        await self._require_house_owner(landlord_id, house_id)
        room = await self.room_repo.get_by_id(room_id)
        if room is None or room.house_id != house_id:
            raise NotFoundError("Room not found")
        room = await self.room_repo.update(room, **request.model_dump(exclude_unset=True))
        return room_to_dict(room)

    async def delete_room(self, landlord_id: str, house_id: str, room_id: str) -> None:
        await self._require_house_owner(landlord_id, house_id)
        room = await self.room_repo.get_by_id(room_id)
        if room is None or room.house_id != house_id:
            raise NotFoundError("Room not found")
        await self.room_repo.delete(room)

    async def update_amenities(
        self, landlord_id: str, house_id: str, request: AmenitiesUpdateRequest
    ) -> dict:
        await self._require_house_owner(landlord_id, house_id)
        return await HouseService(self.house_repo, self.room_repo).update_amenities(
            house_id, request.amenities
        )

    async def get_payment_details(self, landlord_id: str) -> dict | None:
        detail = await self.payment_detail_repo.get_by_landlord(landlord_id)
        return landlord_payment_detail_to_dict(detail) if detail else None

    async def upsert_payment_details(
        self, landlord_id: str, request: LandlordPaymentDetailRequest
    ) -> dict:
        detail = await self.payment_detail_repo.upsert(
            landlord_id, request.model_dump()
        )
        return landlord_payment_detail_to_dict(detail)

    async def list_bookings(self, landlord_id: str) -> list[dict]:
        bookings = await self.booking_repo.list_by_landlord(landlord_id)
        return [booking_to_dict(booking) for booking in bookings]

    async def update_booking_status(
        self,
        landlord_id: str,
        booking_id: str,
        request: BookingStatusUpdateRequest,
    ) -> dict:
        service = BookingService(
            self.booking_repo,
            self.house_repo,
            self.room_repo,
            self.notification_repo,
        )
        return await service.update_status(
            booking_id,
            request.status,
            actor_id=landlord_id,
            landlord_only=True,
        )

    async def _require_house_owner(self, landlord_id: str, house_id: str) -> None:
        house = await self.house_repo.get_by_id(house_id)
        if house is None:
            raise NotFoundError("House not found")
        if house.landlord_id != landlord_id:
            raise AuthError("Landlord access denied")
