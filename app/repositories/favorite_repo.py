"""Repository operations for favorites."""

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.exceptions import ConflictError
from app.models.favorite import Favorite
from app.models.house import House
from app.repositories.base import BaseRepository


class FavoriteRepository(BaseRepository):
    async def list_by_user(self, user_id: str) -> list[Favorite]:
        result = await self.db.execute(
            select(Favorite)
            .options(
                selectinload(Favorite.house),
                selectinload(Favorite.house).selectinload(House.university),
                selectinload(Favorite.house).selectinload(House.amenities),
                selectinload(Favorite.house).selectinload(House.images),
                selectinload(Favorite.house).selectinload(House.nearby_universities),
            )
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc())
        )
        return list(result.scalars().unique().all())

    async def add(self, user_id: str, house_id: str) -> Favorite:
        favorite = Favorite(user_id=user_id, house_id=house_id)
        self.db.add(favorite)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ConflictError("House already in favorites") from exc
        await self.db.refresh(favorite)
        return favorite

    async def remove(self, user_id: str, house_id: str) -> bool:
        result = await self.db.execute(
            select(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.house_id == house_id,
            )
        )
        favorite = result.scalar_one_or_none()
        if favorite is None:
            return False
        await self.db.execute(
            delete(Favorite).where(Favorite.id == favorite.id)
        )
        await self.db.commit()
        return True
