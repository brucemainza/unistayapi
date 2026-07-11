"""Pydantic schemas for authentication requests and responses."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2)
    phone: str = Field(..., pattern=r"^\d{10}$")
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = Field(..., pattern=r"^(student|landlord)$")


class LoginRequest(BaseModel):
    phone: str = Field(..., pattern=r"^\d{10}$")
    password: str = Field(..., min_length=6)


class VerifyOtpRequest(BaseModel):
    user_id: str
    code: str = Field(..., pattern=r"^\d{5}$")


class ResendOtpRequest(BaseModel):
    user_id: str


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., pattern=r"^\d{6}$")


class ResendEmailOtpRequest(BaseModel):
    email: EmailStr


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    phone: str
    email: str
    role: str
    is_verified: bool
    email_verified: bool


class TokenResponse(BaseModel):
    token: str
    user: dict
