"""User profile business logic."""

from sqlalchemy import func, select

from app.exceptions import ConflictError, NotFoundError
from app.models.booking import Booking
from app.models.favorite import Favorite
from app.models.payment import Payment
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services.serializers import booking_to_dict, house_to_dict


class UserService:
    """High-level service for reading and updating user profiles."""

    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def get_profile(self, user_id: str) -> dict:
        """Return the public profile for a user."""
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return UserResponse.model_validate(user).model_dump()

    async def update_profile(self, user_id: str, request: UserUpdateRequest) -> dict:
        """Update the user's profile with the provided fields."""
        update_data = request.model_dump(exclude_unset=True)
        if "phone" in update_data and update_data["phone"]:
            existing = await self.user_repo.get_by_phone(update_data["phone"])
            if existing is not None and existing.id != user_id:
                raise ConflictError("Phone already registered")
        if "email" in update_data and update_data["email"]:
            existing = await self.user_repo.get_by_email(update_data["email"])
            if existing is not None and existing.id != user_id:
                raise ConflictError("Email already registered")
        user = await self.user_repo.update(user_id, **update_data)
        return UserResponse.model_validate(user).model_dump()

    async def get_stats(self, user_id: str) -> dict:
        """Return aggregate counts for the user's activity."""
        bookings_count = await self.user_repo.db.scalar(
            select(func.count(Booking.id)).where(Booking.student_id == user_id)
        )
        favorites_count = await self.user_repo.db.scalar(
            select(func.count(Favorite.id)).where(Favorite.user_id == user_id)
        )
        payments_count = await self.user_repo.db.scalar(
            select(func.count(Payment.id))
            .join(Booking, Payment.booking_id == Booking.id)
            .where(Booking.student_id == user_id)
        )
        return {
            "bookings_count": int(bookings_count or 0),
            "favorites_count": int(favorites_count or 0),
            "payments_count": int(payments_count or 0),
        }

    async def get_accommodation(self, user_id: str) -> dict:
        """Return the user's current booking and house information."""
        result = await self.user_repo.db.execute(
            select(Booking)
            .where(
                Booking.student_id == user_id,
                Booking.status.in_(("pending", "confirmed")),
            )
            .order_by(Booking.created_at.desc())
            .limit(1)
        )
        booking = result.scalar_one_or_none()
        return {
            "current_booking": booking_to_dict(booking) if booking else None,
            "current_house": house_to_dict(booking.house)
            if booking and booking.house
            else None,
        }
