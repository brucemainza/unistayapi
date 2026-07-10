"""Landlords router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import LandlordUser, get_db
from app.repositories.booking_repo import BookingRepository
from app.repositories.house_repo import HouseRepository
from app.repositories.landlord_payment_detail_repo import LandlordPaymentDetailRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.room_repo import RoomRepository
from app.schemas.booking import BookingStatusUpdateRequest
from app.schemas.common import envelope
from app.schemas.house import AmenitiesUpdateRequest, HouseCreateRequest, HouseUpdateRequest
from app.schemas.landlord import LandlordPaymentDetailRequest
from app.schemas.room import RoomCreateRequest, RoomUpdateRequest
from app.services.landlord_service import LandlordService

router = APIRouter()


def _service(db: AsyncSession) -> LandlordService:
    return LandlordService(
        HouseRepository(db),
        RoomRepository(db),
        BookingRepository(db),
        LandlordPaymentDetailRepository(db),
        NotificationRepository(db),
    )


@router.get("/me/houses")
async def my_houses(
    current_user: LandlordUser, db: AsyncSession = Depends(get_db)
) -> dict:
    houses = await _service(db).list_houses(current_user.id)
    return envelope(True, "Landlord houses retrieved", houses)


@router.post("/houses")
async def create_house(
    body: HouseCreateRequest,
    current_user: LandlordUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    house = await _service(db).create_house(current_user.id, body)
    return envelope(True, "House created", house)


@router.patch("/houses/{house_id}")
async def update_house(
    house_id: str,
    body: HouseUpdateRequest,
    current_user: LandlordUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    house = await _service(db).update_house(current_user.id, house_id, body)
    return envelope(True, "House updated", house)


@router.delete("/houses/{house_id}")
async def delete_house(
    house_id: str, current_user: LandlordUser, db: AsyncSession = Depends(get_db)
) -> dict:
    await _service(db).delete_house(current_user.id, house_id)
    return envelope(True, "House deleted", None)


@router.post("/houses/{house_id}/rooms")
async def add_room(
    house_id: str,
    body: RoomCreateRequest,
    current_user: LandlordUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    room = await _service(db).add_room(current_user.id, house_id, body)
    return envelope(True, "Room created", room)


@router.patch("/houses/{house_id}/rooms/{room_id}")
async def update_room(
    house_id: str,
    room_id: str,
    body: RoomUpdateRequest,
    current_user: LandlordUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    room = await _service(db).update_room(current_user.id, house_id, room_id, body)
    return envelope(True, "Room updated", room)


@router.delete("/houses/{house_id}/rooms/{room_id}")
async def delete_room(
    house_id: str,
    room_id: str,
    current_user: LandlordUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _service(db).delete_room(current_user.id, house_id, room_id)
    return envelope(True, "Room deleted", None)


@router.patch("/houses/{house_id}/amenities")
async def update_amenities(
    house_id: str,
    body: AmenitiesUpdateRequest,
    current_user: LandlordUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    house = await _service(db).update_amenities(current_user.id, house_id, body)
    return envelope(True, "Amenities updated", house)


@router.get("/payment-details")
async def get_payment_details(
    current_user: LandlordUser, db: AsyncSession = Depends(get_db)
) -> dict:
    details = await _service(db).get_payment_details(current_user.id)
    return envelope(True, "Payment details retrieved", details)


@router.put("/payment-details")
async def upsert_payment_details(
    body: LandlordPaymentDetailRequest,
    current_user: LandlordUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    details = await _service(db).upsert_payment_details(current_user.id, body)
    return envelope(True, "Payment details saved", details)


@router.get("/bookings")
async def landlord_bookings(
    current_user: LandlordUser, db: AsyncSession = Depends(get_db)
) -> dict:
    bookings = await _service(db).list_bookings(current_user.id)
    return envelope(True, "Landlord bookings retrieved", bookings)


@router.patch("/bookings/{booking_id}/status")
async def update_landlord_booking_status(
    booking_id: str,
    body: BookingStatusUpdateRequest,
    current_user: LandlordUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    booking = await _service(db).update_booking_status(
        current_user.id, booking_id, body
    )
    return envelope(True, "Booking status updated", booking)
