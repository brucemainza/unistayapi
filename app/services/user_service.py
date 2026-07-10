"""User profile business logic."""

from app.exceptions import NotFoundError
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserResponse, UserUpdateRequest


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
        user = await self.user_repo.update(user_id, **update_data)
        return UserResponse.model_validate(user).model_dump()

    async def get_stats(self, user_id: str) -> dict:
        """Return aggregate counts for the user's activity.

        Placeholder counts are returned until dedicated repositories for
        bookings, favorites, and payments are available.
        """
        return {
            "bookings_count": 0,
            "favorites_count": 0,
            "payments_count": 0,
        }

    async def get_accommodation(self, user_id: str) -> dict:
        """Return the user's current booking and house information.

        A placeholder response is returned until booking/house lookups are
        wired into the service.
        """
        return {
            "current_booking": None,
            "current_house": None,
        }
