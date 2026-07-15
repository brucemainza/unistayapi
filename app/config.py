from logging import Logger

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    jwt_secret: str
    jwt_expires_in: int = 86400
    lenco_mock: bool = True
    lenco_api_key: str | None = None
    lenco_base_url: str = "https://api.lenco.co"
    lenco_webhook_secret: str | None = None
    environment: str = "development"
    google_maps_server_key: str | None = None
    google_maps_signing_secret: str | None = None
    google_maps_places_region: str = "ZM"
    redis_url: str | None = None
    resend_api_key: str | None = None
    resend_from_email: str = "UniStay <no-reply@mainzabruce.online>"
    otp_ttl_seconds: int = 600
    otp_resend_cooldown: int = 60
    otp_max_attempts: int = 5
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None
    cloudinary_folder: str = "unistay"
    cloudinary_secure: bool = True
    mock_otp_bypass: bool = False

    _placeholder_values = {
        "",
        "change-me",
        "change-me-to-a-long-random-value",
        "your-api-key",
        "your-secret",
        "placeholder",
        "mock",
        "test",
    }

    def _is_missing_or_placeholder(self, value: str | None) -> bool:
        if value is None:
            return True
        normalized = value.strip()
        if not normalized:
            return True
        lowered = normalized.lower()
        return lowered in self._placeholder_values or "your-" in lowered

    def validate_for_environment(self, logger: Logger | None = None) -> None:
        """Validate required settings for the active environment.

        In production this raises ``RuntimeError`` when a required variable is
        missing. When a logger is supplied the reason is logged at ERROR first,
        so a misconfigured deploy emits a useful structured line instead of a
        bare traceback. Non-production environments skip this check.
        """
        if self.environment != "production":
            return

        missing_or_placeholder: list[str] = []
        required_values = {
            "DATABASE_URL": self.database_url,
            "JWT_SECRET": self.jwt_secret,
            "LENCO_API_KEY": self.lenco_api_key,
            "LENCO_WEBHOOK_SECRET": self.lenco_webhook_secret,
            "GOOGLE_MAPS_SERVER_KEY": self.google_maps_server_key,
            "REDIS_URL": self.redis_url,
            "RESEND_API_KEY": self.resend_api_key,
            "CLOUDINARY_CLOUD_NAME": self.cloudinary_cloud_name,
            "CLOUDINARY_API_KEY": self.cloudinary_api_key,
            "CLOUDINARY_API_SECRET": self.cloudinary_api_secret,
        }
        for name, value in required_values.items():
            if self._is_missing_or_placeholder(value):
                missing_or_placeholder.append(name)

        if len(self.jwt_secret) < 32:
            missing_or_placeholder.append("JWT_SECRET")
        if self.lenco_mock:
            missing_or_placeholder.append("LENCO_MOCK=false")

        # Production must never accept the phone-OTP mock bypass; force-disable
        # it regardless of what the env var says so a deploy cannot accidentally
        # accept any 5-digit code by mistake.
        if getattr(self, "mock_otp_bypass", True):
            self.mock_otp_bypass = False

        if missing_or_placeholder:
            reason = (
                "Missing, placeholder, or unsafe production settings: "
                + ", ".join(sorted(set(missing_or_placeholder)))
            )
            if logger is not None:
                logger.error(reason)
            raise RuntimeError(reason)


settings = Settings()
