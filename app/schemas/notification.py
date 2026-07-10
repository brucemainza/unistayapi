"""Schemas for user notifications."""

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    title: str
    body: str
    isRead: bool
    createdAt: str
