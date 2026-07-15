"""Landlords router."""

from fastapi import APIRouter, BackgroundTasks, Depends

from app.dependencies import LandlordUser
from app.providers import get_house_service, get_landlord_service
from app.schemas.booking import BookingStatusUpdateRequest
from app.schemas.common import envelope
from app.schemas.house import AmenitiesUpdateRequest, HouseCreateRequest, HouseUpdateRequest
from app.schemas.landlord import LandlordPaymentDetailRequest
from app.schemas.room import RoomCreateRequest, RoomUpdateRequest
from app.services.house_service import HouseService
from app.services.landlord_service import LandlordService

router = APIRouter()


@router.get("/me/houses")
async def my_houses(
    current_user: LandlordUser,
    service: LandlordService = Depends(get_landlord_service),
) -> dict:
    houses = await service.list_houses(current_user.id)
    return envelope(True, "Landlord houses retrieved", houses)


@router.post("/houses")
async def create_house(
    body: HouseCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: LandlordUser,
    service: LandlordService = Depends(get_landlord_service),
    house_service: HouseService = Depends(get_house_service),
) -> dict:
    house = await service.create_house(current_user.id, body)
    if body.latitude is not None and body.longitude is not None:
        background_tasks.add_task(
            house_service.reverse_geocode_and_update,
            house["id"],
            body.latitude,
            body.longitude,
        )
    return envelope(True, "House created", house)


@router.patch("/houses/{house_id}")
async def update_house(
    house_id: str,
    body: HouseUpdateRequest,
    current_user: LandlordUser,
    service: LandlordService = Depends(get_landlord_service),
) -> dict:
    house = await service.update_house(current_user.id, house_id, body)
    return envelope(True, "House updated", house)


@router.delete("/houses/{house_id}")
async def delete_house(
    house_id: str,
    current_user: LandlordUser,
    service: LandlordService = Depends(get_landlord_service),
) -> dict:
    await service.delete_house(current_user.id, house_id)
    return envelope(True, "House deleted", None)


@router.post("/houses/{house_id}/rooms")
async def add_room(
    house_id: str,
    body: RoomCreateRequest,
    current_user: LandlordUser,
    service: LandlordService = Depends(get_landlord_service),
) -> dict:
    room = await service.add_room(current_user.id, house_id, body)
    return envelope(True, "Room created", room)


@router.patch("/houses/{house_id}/rooms/{room_id}")
async def update_room(
    house_id: str,
    room_id: str,
    body: RoomUpdateRequest,
    current_user: LandlordUser,
    service: LandlordService = Depends(get_landlord_service),
) -> dict:
    room = await service.update_room(current_user.id, house_id, room_id, body)
    return envelope(True, "Room updated", room)


@router.delete("/houses/{house_id}/rooms/{room_id}")
async def delete_room(
    house_id: str,
    room_id: str,
    current_user: LandlordUser,
    service: LandlordService = Depends(get_landlord_service),
) -> dict:
    await service.delete_room(current_user.id, house_id, room_id)
    return envelope(True, "Room deleted", None)


@router.patch("/houses/{house_id}/amenities")
async def update_amenities(
    house_id: str,
    body: AmenitiesUpdateRequest,
    current_user: LandlordUser,
    service: LandlordService = Depends(get_landlord_service),
) -> dict:
    house = await service.update_amenities(current_user.id, house_id, body)
    return envelope(True, "Amenities updated", house)


@router.get("/payment-details")
async def get_payment_details(
    current_user: LandlordUser,
    service: LandlordService = Depends(get_landlord_service),
) -> dict:
    details = await service.get_payment_details(current_user.id)
    return envelope(True, "Payment details retrieved", details)


@router.put("/payment-details")
async def upsert_payment_details(
    body: LandlordPaymentDetailRequest,
    current_user: LandlordUser,
    service: LandlordService = Depends(get_landlord_service),
) -> dict:
    details = await service.upsert_payment_details(current_user.id, body)
    return envelope(True, "Payment details saved", details)


@router.get("/bookings")
async def landlord_bookings(
    current_user: LandlordUser,
    service: LandlordService = Depends(get_landlord_service),
) -> dict:
    bookings = await service.list_bookings(current_user.id)
    return envelope(True, "Landlord bookings retrieved", bookings)


@router.patch("/bookings/{booking_id}/status")
async def update_landlord_booking_status(
    booking_id: str,
    body: BookingStatusUpdateRequest,
    current_user: LandlordUser,
    service: LandlordService = Depends(get_landlord_service),
) -> dict:
    booking = await service.update_booking_status(
        current_user.id, booking_id, body
    )
    return envelope(True, "Booking status updated", booking)
