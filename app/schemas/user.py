"""Pydantic schemas for user profile requests and responses."""

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    """Public user profile representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    phone: str
    email: str
    role: str
    is_verified: bool


class UserUpdateRequest(BaseModel):
    """Fields that may be updated on a user profile."""

    full_name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
