"""DTO serializers for ORM models used by multiple services."""

from decimal import Decimal

from app.geo import parse_point
from app.models.booking import Booking
from app.models.house import House
from app.models.landlord_payment_detail import LandlordPaymentDetail
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.room import Room


def room_to_dict(room: Room) -> dict:
    return {
        "id": room.id,
        "houseId": room.house_id,
        "type": room.type,
        "rent": room.rent,
        "deposit": room.deposit,
        "available": room.available,
        "features": room.features or [],
    }


def house_to_dict(house: House) -> dict:
    latitude, longitude = parse_point(house.coords)
    return {
        "id": house.id,
        "name": house.name,
        "location": house.location,
        "university": house.university.name if house.university else None,
        "universityId": house.university_id,
        "price": house.price,
        "walkTime": house.walk_time,
        "driveDistance": house.drive_distance,
        "rating": house.rating,
        "availableSpaces": house.available_spaces,
        "accent": house.accent,
        "amenities": [item.name for item in house.amenities],
        "imageUrls": [item.url for item in house.images],
        "paymentMethods": house.payment_methods or [],
        "nearbyUniversities": [
            {"name": item.name, "distance": item.distance}
            for item in house.nearby_universities
        ],
        "latitude": latitude,
        "longitude": longitude,
    }


def booking_to_dict(booking: Booking) -> dict:
    return {
        "id": booking.id,
        "studentId": booking.student_id,
        "houseId": booking.house_id,
        "roomId": booking.room_id,
        "moveInDate": booking.move_in_date.isoformat(),
        "status": booking.status,
        "note": booking.note,
        "houseName": booking.house.name if booking.house else None,
        "roomType": booking.room.type if booking.room else None,
        "createdAt": booking.created_at.isoformat(),
        "updatedAt": booking.updated_at.isoformat(),
    }


def payment_status_for_client(status: str) -> str:
    return "successful" if status == "completed" else status


def payment_to_dict(payment: Payment) -> dict:
    amount: Decimal | str = payment.amount
    return {
        "reference": payment.reference,
        "status": payment_status_for_client(payment.status),
        "amount": str(amount),
        "currency": payment.currency,
        "lencoReference": payment.lenco_reference,
    }


def notification_to_dict(notification: Notification) -> dict:
    return {
        "id": notification.id,
        "title": notification.title,
        "body": notification.body,
        "isRead": notification.is_read,
        "createdAt": notification.created_at.isoformat(),
    }


def landlord_payment_detail_to_dict(detail: LandlordPaymentDetail) -> dict:
    return {
        "id": detail.id,
        "bankName": detail.bank_name,
        "accountName": detail.account_name,
        "accountNumber": detail.account_number,
        "mobileMoneyProvider": detail.mobile_money_provider,
        "mobileMoneyNumber": detail.mobile_money_number,
        "isDefault": detail.is_default,
    }
