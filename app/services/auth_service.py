"""Authentication business logic: registration, login, JWT, and OTP."""

import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select

from app.config import settings
from app.exceptions import AuthError, ConflictError, NotFoundError, ValidationError
from app.models.otp import Otp
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, UserResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
    def create_access_token(data: dict) -> str:
        """Encode a JWT access token with the configured secret and expiry."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(seconds=settings.jwt_expires_in)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.jwt_secret, algorithm="HS256")

    @staticmethod
    def verify_token(token: str) -> dict:
        """Decode and return a JWT payload, raising ``AuthError`` on failure."""
        try:
            return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        except JWTError as exc:
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
                    Otp.code == code,
                    Otp.used.is_(False),
                    Otp.expires_at > now,
                )
                .order_by(Otp.created_at.desc())
            )
            otp = result.scalar_one_or_none()
            if otp is None:
                raise AuthError("Invalid or expired OTP")
            otp.used = True
        else:
            # Mock mode: accept any 5-digit code.
            pass

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
        expires_in_seconds = 600

        if settings.environment == "production":
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=expires_in_seconds
            )
            otp = Otp(user_id=user.id, code=code, expires_at=expires_at)
            self.user_repo.db.add(otp)
            await self.user_repo.db.commit()

        return {"code": code, "expires_in": expires_in_seconds}
