"""Authentication router."""

import redis.asyncio as aioredis
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_db, get_redis
from app.exceptions import AuthError, ConflictError, RateLimitError
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    ResendEmailOtpRequest,
    ResendOtpRequest,
    UserResponse,
    VerifyEmailRequest,
    VerifyOtpRequest,
)
from app.schemas.common import envelope
from app.services.auth_service import AuthService
from app.services.email import send_otp_email
from app.services.otp import issue_otp, verify_otp as verify_email_otp

router = APIRouter()

_SIGNUP_RATE_LIMIT = 5
_SIGNUP_RATE_WINDOW = 60


async def _signup_rate_limit(request: Request, redis: aioredis.Redis) -> None:
    """Enforce a per-IP fixed-window limit on signup attempts."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    elif request.client is not None:
        ip = request.client.host
    else:
        ip = "unknown"

    key = f"rate_limit:signup:{ip}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, _SIGNUP_RATE_WINDOW)
    if current > _SIGNUP_RATE_LIMIT:
        raise RateLimitError("Too many signup attempts; please try again later")


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


@router.post("/signup", status_code=201)
async def signup(
    body: RegisterRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create an unverified account and send a 6-digit email OTP."""
    await _signup_rate_limit(request, redis)

    service = AuthService(UserRepository(db))
    user = await service.create_user(body)

    code = await issue_otp(redis, user.email)
    background_tasks.add_task(send_otp_email, user.email, code)

    return envelope(
        True,
        "Verification code sent",
        {"id": user.id, "email": user.email},
    )


@router.post("/verify-email")
async def verify_email(
    body: VerifyEmailRequest,
    redis: aioredis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify a 6-digit email OTP and mark the account as verified."""
    repo = UserRepository(db)
    user = await repo.get_by_email(body.email)

    # Always run verification so response timing does not leak registration status.
    ok = await verify_email_otp(redis, body.email, body.code)

    if not ok or user is None:
        raise AuthError("Invalid or expired code")

    user.email_verified = True
    user.is_verified = True
    await db.commit()
    await db.refresh(user)

    token = AuthService.create_access_token({"sub": user.id})
    return envelope(
        True,
        "Email verified",
        {"token": token, "user": UserResponse.model_validate(user).model_dump()},
    )


@router.post("/resend-email-otp")
async def resend_email_otp(
    body: ResendEmailOtpRequest,
    background_tasks: BackgroundTasks,
    redis: aioredis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Resend the email OTP to a registered address."""
    repo = UserRepository(db)
    user = await repo.get_by_email(body.email)

    # Don't reveal whether the email is registered.
    if user is None:
        return envelope(
            True,
            "If your email is registered, a code has been sent",
            None,
        )

    code = await issue_otp(redis, user.email)
    background_tasks.add_task(send_otp_email, user.email, code)

    return envelope(True, "Verification code sent", None)


@router.get("/me")
async def me(current_user: CurrentUser) -> dict:
    """Return the currently authenticated user's profile."""
    return envelope(
        True, "User profile", UserResponse.model_validate(current_user).model_dump()
    )
