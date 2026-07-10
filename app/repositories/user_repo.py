"""User repository for account lookups and persistence."""

from sqlalchemy import select

from app.exceptions import NotFoundError
from app.models.user import User
from app.repositories.base import BaseRepository

_DEV_EMAIL = "dev@unistay.local"
_DEV_PHONE = "+233000000000"


class UserRepository(BaseRepository):
    """Persistence operations for ``User`` records."""

    async def get_by_phone(self, phone: str) -> User | None:
        result = await self.db.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user_id: str, **kwargs) -> User:
        """Update a user's profile fields and return the refreshed user."""
        user = await self.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")

        for key, value in kwargs.items():
            if value is not None:
                setattr(user, key, value)

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def exists_by_phone_or_email(self, phone: str, email: str) -> bool:
        result = await self.db.execute(
            select(User).where((User.phone == phone) | (User.email == email))
        )
        return result.scalar_one_or_none() is not None

    async def get_dev_user(self) -> User:
        """Return the development student user, creating it if necessary."""
        result = await self.db.execute(select(User).where(User.email == _DEV_EMAIL))
        user = result.scalar_one_or_none()
        if user is not None:
            return user

        user = User(
            full_name="Development Student",
            phone=_DEV_PHONE,
            email=_DEV_EMAIL,
            password_hash="dev-password-not-used",
            role="student",
            is_verified=True,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
