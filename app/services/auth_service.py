"""Authentication business logic: registration, login, JWT, and OTP."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from sqlalchemy import select

from app.config import settings
from app.exceptions import (
    AuthError,
    ConflictError,
    DeliveryError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from app.models.otp import Otp
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, UserResponse
from app.services.email import send_otp_email

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


class AuthService:
    """High-level service for account authentication and verification."""

    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    def _user_to_dict(self, user: User) -> dict:
        return UserResponse.model_validate(user).model_dump()

    @staticmethod
    def _generate_otp() -> str:
        return f"{secrets.randbelow(100000):05d}"

    @staticmethod
    def _hash_otp(user_id: str, code: str) -> str:
        return hmac.new(
            settings.jwt_secret.encode("utf-8"),
            f"{user_id}:{code}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def create_access_token(data: dict) -> str:
        """Encode a JWT access token with the configured secret and expiry."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(seconds=settings.jwt_expires_in)
        to_encode.update({"exp": int(expire.timestamp())})

        header = {"alg": "HS256", "typ": "JWT"}
        signing_input = ".".join(
            [
                _base64url_encode(json.dumps(header, separators=(",", ":")).encode()),
                _base64url_encode(
                    json.dumps(to_encode, separators=(",", ":")).encode()
                ),
            ]
        )
        signature = hmac.new(
            settings.jwt_secret.encode("utf-8"),
            signing_input.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return f"{signing_input}.{_base64url_encode(signature)}"

    @staticmethod
    def verify_token(token: str) -> dict:
        """Decode and return a JWT payload, raising ``AuthError`` on failure."""
        try:
            header_segment, payload_segment, signature_segment = token.split(".")
            signing_input = f"{header_segment}.{payload_segment}"
            expected_signature = hmac.new(
                settings.jwt_secret.encode("utf-8"),
                signing_input.encode("ascii"),
                hashlib.sha256,
            ).digest()
            supplied_signature = _base64url_decode(signature_segment)
            if not hmac.compare_digest(expected_signature, supplied_signature):
                raise ValueError("Invalid JWT signature")

            header = json.loads(_base64url_decode(header_segment))
            if header.get("alg") != "HS256":
                raise ValueError("Unexpected JWT algorithm")

            payload = json.loads(_base64url_decode(payload_segment))
            exp = payload.get("exp")
            if not isinstance(exp, int | float) or exp < time.time():
                raise ValueError("Expired JWT")
            return payload
        except Exception as exc:
            raise AuthError("Invalid or expired token") from exc

    async def create_user(self, request: RegisterRequest) -> User:
        """Create and persist a new unverified user account."""
        exists = await self.user_repo.exists_by_phone_or_email(
            request.phone, request.email
        )
        if exists:
            raise ConflictError("Phone or email already registered")

        user = User(
            full_name=request.full_name,
            phone=request.phone,
            email=request.email,
            password_hash=pwd_context.hash(request.password),
            role=request.role,
            is_verified=False,
            email_verified=False,
        )
        return await self.user_repo.create(user)

    async def register(self, request: RegisterRequest) -> dict:
        """Create a new user account and return an access token."""
        user = await self.create_user(request)
        token = self.create_access_token({"sub": user.id})
        return {"token": token, "user": self._user_to_dict(user)}

    async def login(self, request: LoginRequest) -> dict:
        """Authenticate a user by phone/password and return an access token."""
        user = await self.user_repo.get_by_phone(request.phone)
        if user is None or not pwd_context.verify(
            request.password, user.password_hash
        ):
            raise AuthError("Invalid phone or password")

        token = self.create_access_token({"sub": user.id})
        return {"token": token, "user": self._user_to_dict(user)}

    async def verify_otp(self, user_id: str, code: str) -> dict:
        """Validate an OTP and mark the user as verified."""
        if not isinstance(code, str) or not code.isdigit() or len(code) != 5:
            raise ValidationError("OTP must be a 5-digit code")

        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")

        if settings.environment == "production":
            now = datetime.now(timezone.utc)
            result = await self.user_repo.db.execute(
                select(Otp)
                .where(
                    Otp.user_id == user_id,
                    Otp.used.is_(False),
                    Otp.expires_at > now,
                )
                .order_by(Otp.created_at.desc())
                .with_for_update()
            )
            otp = result.scalar_one_or_none()
            if otp is None or not hmac.compare_digest(
                otp.code, self._hash_otp(user_id, code)
            ):
                if otp is not None:
                    otp.attempt_count += 1
                    if otp.attempt_count >= settings.otp_max_attempts:
                        otp.used = True
                    await self.user_repo.db.commit()
                if otp is not None and otp.attempt_count >= settings.otp_max_attempts:
                    raise RateLimitError("Too many OTP attempts; request a new code")
                raise AuthError("Invalid or expired OTP")
            otp.used = True
        elif getattr(settings, "mock_otp_bypass", False):
            # Explicit test/development bypass. Gated by `MOCK_OTP_BYPASS` and
            # force-disabled in `Settings.validate_for_environment` for prod so
            # staging environments are not silently wide open.
            pass
        else:
            # Non-production, non-bypass path: still validate against the OTP
            # table so a stale staging deploy can't accept every 5-digit code.
            result = await self.user_repo.db.execute(
                select(Otp)
                .where(
                    Otp.user_id == user_id,
                    Otp.used.is_(False),
                )
                .order_by(Otp.created_at.desc())
                .with_for_update()
            )
            otp = result.scalar_one_or_none()
            if otp is None or not hmac.compare_digest(
                otp.code, self._hash_otp(user_id, code)
            ):
                if otp is not None:
                    otp.attempt_count += 1
                    if otp.attempt_count >= settings.otp_max_attempts:
                        otp.used = True
                    await self.user_repo.db.commit()
                if otp is not None and otp.attempt_count >= settings.otp_max_attempts:
                    raise RateLimitError("Too many OTP attempts; request a new code")
                raise AuthError("Invalid or expired OTP")
            otp.used = True

        user.is_verified = True
        await self.user_repo.db.commit()
        await self.user_repo.db.refresh(user)

        token = self.create_access_token({"sub": user.id})
        return {"token": token, "user": self._user_to_dict(user)}

    async def resend_otp(self, user_id: str) -> dict:
        """Generate a new OTP for the given user."""
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")

        code = self._generate_otp()

        if settings.environment == "production" or not getattr(
            settings, "mock_otp_bypass", False
        ):
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=settings.otp_ttl_seconds
            )
            otp = Otp(
                user_id=user.id,
                code=self._hash_otp(user.id, code),
                expires_at=expires_at,
            )
            self.user_repo.db.add(otp)
            await self.user_repo.db.commit()

            if not await send_otp_email(user.email, code):
                raise DeliveryError("OTP email could not be sent")

        response = {"expires_in": settings.otp_ttl_seconds}
        if settings.environment != "production" and getattr(
            settings, "mock_otp_bypass", False
        ):
            response["code"] = code
        return response
