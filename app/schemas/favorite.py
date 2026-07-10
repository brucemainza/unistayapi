"""Schemas for user favorite houses."""

from pydantic import BaseModel


class FavoriteCreateRequest(BaseModel):
    house_id: str
