"""Authentication router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_db
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    ResendOtpRequest,
    UserResponse,
    VerifyOtpRequest,
)
from app.schemas.common import envelope
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """Register a new student or landlord account."""
    service = AuthService(UserRepository(db))
    result = await service.register(body)
    return envelope(True, "Registration successful", result)


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """Log in with phone number and password."""
    service = AuthService(UserRepository(db))
    result = await service.login(body)
    return envelope(True, "Login successful", result)


@router.post("/verify-otp")
async def verify_otp(
    body: VerifyOtpRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """Verify a 5-digit OTP and activate the account."""
    service = AuthService(UserRepository(db))
    result = await service.verify_otp(body.user_id, body.code)
    return envelope(True, "OTP verified", result)


@router.post("/resend-otp")
async def resend_otp(
    body: ResendOtpRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """Request a new OTP."""
    service = AuthService(UserRepository(db))
    result = await service.resend_otp(body.user_id)
    return envelope(True, "OTP resent", result)


@router.get("/me")
async def me(current_user: CurrentUser) -> dict:
    """Return the currently authenticated user's profile."""
    return envelope(
        True, "User profile", UserResponse.model_validate(current_user).model_dump()
    )
