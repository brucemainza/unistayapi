"""Business logic for user notifications."""

from app.exceptions import NotFoundError
from app.repositories.notification_repo import NotificationRepository
from app.services.serializers import notification_to_dict


class NotificationService:
    def __init__(self, repo: NotificationRepository) -> None:
        self.repo = repo

    async def list_notifications(self, user_id: str) -> list[dict]:
        notifications = await self.repo.list_by_user(user_id)
        return [notification_to_dict(item) for item in notifications]

    async def mark_read(self, user_id: str, notification_id: str) -> dict:
        notification = await self.repo.mark_read(user_id, notification_id)
        if notification is None:
            raise NotFoundError("Notification not found")
        return notification_to_dict(notification)

    async def mark_all_read(self, user_id: str) -> dict:
        count = await self.repo.mark_all_read(user_id)
        return {"updated": count}
