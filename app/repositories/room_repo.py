"""Room repository for persistence operations."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.room import Room
from app.repositories.base import BaseRepository


class RoomRepository(BaseRepository):
    """Persistence operations for ``Room`` records."""

    async def get_by_house_id(self, house_id: str) -> list[Room]:
        """Return all rooms for a given house, ordered by rent ascending."""
        result = await self.db.execute(
            select(Room)
            .where(Room.house_id == house_id)
            .order_by(Room.rent)
        )
        return list(result.scalars().all())

    async def get_by_id(self, room_id: str) -> Room | None:
        """Return a single room by primary key."""
        result = await self.db.execute(
            select(Room).where(Room.id == room_id)
        )
        return result.scalar_one_or_none()

    async def create(self, room: Room) -> Room:
        """Persist a new room and return it."""
        self.db.add(room)
        await self.db.commit()
        await self.db.refresh(room)
        return room

    async def update(self, room: Room, **kwargs) -> Room:
        """Update room fields and return the refreshed room."""
        for key, value in kwargs.items():
            if value is not None:
                setattr(room, key, value)
        await self.db.commit()
        await self.db.refresh(room)
        return room

    async def delete(self, room: Room) -> None:
        """Delete a room."""
        await self.db.delete(room)
        await self.db.commit()
