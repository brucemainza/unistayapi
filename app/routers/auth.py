"""Authentication router."""

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Request

from app.dependencies import CurrentUser, get_redis
from app.exceptions import AuthError, DeliveryError
from app.providers import get_auth_service, get_user_repository
from app.rate_limit import enforce_fixed_window
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    ResendEmailOtpRequest,
    ResendOtpRequest,
    SignupResponse,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
    VerifyOtpRequest,
)
from app.schemas.common import Envelope, envelope
from app.services.auth_service import AuthService
from app.services.email import send_otp_email
from app.services.otp import issue_otp, verify_otp as verify_email_otp

router = APIRouter()

_SIGNUP_RATE_LIMIT = 5
_SIGNUP_RATE_WINDOW = 60
_LOGIN_RATE_LIMIT = 10
_LOGIN_RATE_WINDOW = 60


async def _signup_rate_limit(request: Request, redis: aioredis.Redis) -> None:
    """Enforce a per-IP fixed-window limit on signup attempts via Redis."""
    await enforce_fixed_window(
        redis=redis,
        key_prefix="rate_limit:signup",
        request=request,
        max_requests=_SIGNUP_RATE_LIMIT,
        window_seconds=_SIGNUP_RATE_WINDOW,
        message="Too many signup attempts; please try again later",
    )


async def _login_rate_limit(request: Request, redis: aioredis.Redis) -> None:
    await enforce_fixed_window(
        redis=redis,
        key_prefix="rate_limit:login",
        request=request,
        max_requests=_LOGIN_RATE_LIMIT,
        window_seconds=_LOGIN_RATE_WINDOW,
        message="Too many authentication attempts; please try again later",
    )


@router.post("/register", response_model=Envelope[TokenResponse])
async def register(
    body: RegisterRequest,
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
    service: AuthService = Depends(get_auth_service),
) -> dict:
    """Register a new student or landlord account."""
    await _signup_rate_limit(request, redis)
    result = await service.register(body)
    await service.resend_otp(result["user"]["id"])
    return envelope(True, "Registration successful", result)


@router.post("/login", response_model=Envelope[TokenResponse])
async def login(
    body: LoginRequest,
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
    service: AuthService = Depends(get_auth_service),
) -> dict:
    """Log in with phone number and password."""
    await _login_rate_limit(request, redis)
    result = await service.login(body)
    return envelope(True, "Login successful", result)


@router.post("/verify-otp", response_model=Envelope[TokenResponse])
async def verify_otp(
    body: VerifyOtpRequest,
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
    service: AuthService = Depends(get_auth_service),
) -> dict:
    """Verify a 5-digit OTP and activate the account."""
    await _login_rate_limit(request, redis)
    result = await service.verify_otp(body.user_id, body.code)
    return envelope(True, "OTP verified", result)


@router.post("/resend-otp")
async def resend_otp(
    body: ResendOtpRequest,
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
    service: AuthService = Depends(get_auth_service),
) -> dict:
    """Request a new OTP."""
    await _signup_rate_limit(request, redis)
    result = await service.resend_otp(body.user_id)
    return envelope(True, "OTP resent", result)


@router.post("/signup", status_code=201, response_model=Envelope[SignupResponse])
async def signup(
    body: RegisterRequest,
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
    service: AuthService = Depends(get_auth_service),
) -> dict:
    """Create an unverified account and send a 6-digit email OTP."""
    await _signup_rate_limit(request, redis)

    user = await service.create_user(body)

    code = await issue_otp(redis, user.email)
    if not await send_otp_email(user.email, code):
        raise DeliveryError("Verification email could not be sent")

    return envelope(
        True,
        "Verification code sent",
        {"id": user.id, "email": user.email},
    )


@router.post("/verify-email", response_model=Envelope[TokenResponse])
async def verify_email(
    body: VerifyEmailRequest,
    redis: aioredis.Redis = Depends(get_redis),
    repo: UserRepository = Depends(get_user_repository),
) -> dict:
    """Verify a 6-digit email OTP and mark the account as verified."""
    user = await repo.get_by_email(body.email)

    # Always run verification so response timing does not leak registration status.
    ok = await verify_email_otp(redis, body.email, body.code)

    if not ok or user is None:
        raise AuthError("Invalid or expired code")

    user.email_verified = True
    user.is_verified = True
    await repo.commit()
    await repo.db.refresh(user)

    token = AuthService.create_access_token({"sub": user.id})
    return envelope(
        True,
        "Email verified",
        {"token": token, "user": UserResponse.model_validate(user).model_dump()},
    )


@router.post("/resend-email-otp")
async def resend_email_otp(
    body: ResendEmailOtpRequest,
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
    repo: UserRepository = Depends(get_user_repository),
) -> dict:
    """Resend the email OTP to a registered address."""
    await _signup_rate_limit(request, redis)
    user = await repo.get_by_email(body.email)

    # Don't reveal whether the email is registered.
    if user is None:
        return envelope(
            True,
            "If your email is registered, a code has been sent",
            None,
        )

    code = await issue_otp(redis, user.email)
    if not await send_otp_email(user.email, code):
        raise DeliveryError("Verification email could not be sent")

    return envelope(True, "Verification code sent", None)


@router.get("/me", response_model=Envelope[UserResponse])
async def me(current_user: CurrentUser) -> dict:
    """Return the currently authenticated user's profile."""
    return envelope(
        True, "User profile", UserResponse.model_validate(current_user).model_dump()
    )
