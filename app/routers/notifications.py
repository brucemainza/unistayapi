"""Notifications router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_db
from app.repositories.notification_repo import NotificationRepository
from app.schemas.common import envelope
from app.services.notification_service import NotificationService

router = APIRouter()


def _service(db: AsyncSession) -> NotificationService:
    return NotificationService(NotificationRepository(db))


@router.get("")
async def list_notifications(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict:
    notifications = await _service(db).list_notifications(current_user.id)
    return envelope(True, "Notifications retrieved", notifications)


@router.patch("/read-all")
async def read_all(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict:
    result = await _service(db).mark_all_read(current_user.id)
    return envelope(True, "Notifications marked read", result)


@router.patch("/{notification_id}/read")
async def read_notification(
    notification_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    notification = await _service(db).mark_read(current_user.id, notification_id)
    return envelope(True, "Notification marked read", notification)
