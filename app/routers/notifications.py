"""Notifications router."""

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser
from app.providers import get_notification_service
from app.schemas.common import Envelope, envelope
from app.schemas.notification import NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("", response_model=Envelope[list[NotificationResponse]])
async def list_notifications(
    current_user: CurrentUser,
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    notifications = await service.list_notifications(current_user.id)
    return envelope(True, "Notifications retrieved", notifications)


@router.patch("/read-all")
async def read_all(
    current_user: CurrentUser,
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    result = await service.mark_all_read(current_user.id)
    return envelope(True, "Notifications marked read", result)


@router.patch("/{notification_id}/read", response_model=Envelope[NotificationResponse])
async def read_notification(
    notification_id: str,
    current_user: CurrentUser,
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    notification = await service.mark_read(current_user.id, notification_id)
    return envelope(True, "Notification marked read", notification)
