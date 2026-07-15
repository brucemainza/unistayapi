"""Repository operations for notifications."""

from sqlalchemy import select, update

from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository):
    async def list_by_user(self, user_id: str) -> list[Notification]:
        result = await self.db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, notification: Notification) -> Notification:
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def add(self, notification: Notification) -> Notification:
        """Stage a new notification without committing (unit-of-work friendly)."""
        self.db.add(notification)
        await self.db.flush()
        return notification

    async def commit_and_refresh(self, notification: Notification) -> Notification:
        """Commit the transaction and refresh the notification instance."""
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def mark_read(self, user_id: str, notification_id: str) -> Notification | None:
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notification = result.scalar_one_or_none()
        if notification is None:
            return None
        notification.is_read = True
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def mark_all_read(self, user_id: str) -> int:
        result = await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        await self.db.commit()
        return int(result.rowcount or 0)
