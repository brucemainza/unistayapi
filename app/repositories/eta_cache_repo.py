"""Repository operations for ETA cache."""

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.eta_cache import EtaCache
from app.repositories.base import BaseRepository


class EtaCacheRepository(BaseRepository):
    async def get(
        self, house_id: str, university_id: str, mode: str
    ) -> EtaCache | None:
        result = await self.db.execute(
            select(EtaCache).where(
                EtaCache.house_id == house_id,
                EtaCache.university_id == university_id,
                EtaCache.mode == mode.upper(),
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        house_id: str,
        university_id: str,
        mode: str,
        duration_s: int,
        distance_m: int,
    ) -> EtaCache:
        existing = await self.get(house_id, university_id, mode)
        if existing:
            existing.duration_s = duration_s
            existing.distance_m = distance_m
            existing.computed_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        cache = EtaCache(
            house_id=house_id,
            university_id=university_id,
            mode=mode.upper(),
            duration_s=duration_s,
            distance_m=distance_m,
        )
        self.db.add(cache)
        await self.db.commit()
        await self.db.refresh(cache)
        return cache
