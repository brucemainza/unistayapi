"""Business logic for favorite houses."""

from app.exceptions import NotFoundError
from app.repositories.favorite_repo import FavoriteRepository
from app.repositories.house_repo import HouseRepository
from app.services.serializers import house_to_dict


class FavoriteService:
    def __init__(
        self, favorite_repo: FavoriteRepository, house_repo: HouseRepository
    ) -> None:
        self.favorite_repo = favorite_repo
        self.house_repo = house_repo

    async def list_favorites(self, user_id: str) -> list[dict]:
        favorites = await self.favorite_repo.list_by_user(user_id)
        return [house_to_dict(favorite.house) for favorite in favorites]

    async def add_favorite(self, user_id: str, house_id: str) -> dict:
        house = await self.house_repo.get_by_id(house_id)
        if house is None:
            raise NotFoundError("House not found")
        await self.favorite_repo.add(user_id, house_id)
        return house_to_dict(house)

    async def remove_favorite(self, user_id: str, house_id: str) -> None:
        deleted = await self.favorite_repo.remove(user_id, house_id)
        if not deleted:
            raise NotFoundError("Favorite not found")
