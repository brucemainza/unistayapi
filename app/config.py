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
    otp_ttl_seconds: int = 600
    otp_resend_cooldown: int = 60
    otp_max_attempts: int = 5
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None
    cloudinary_folder: str = "unistay"
    cloudinary_secure: bool = True

    def validate_for_environment(self, logger: Logger | None = None) -> None:
        """Validate required settings for the active environment.

        In production this raises ``RuntimeError`` when a required variable is
        missing. When a logger is supplied the reason is logged at ERROR first,
        so a misconfigured deploy emits a useful structured line instead of a
        bare traceback. Non-production environments skip this check.
        """
        if self.environment != "production":
            return

        missing: list[str] = []
        if not self.google_maps_server_key:
            missing.append("GOOGLE_MAPS_SERVER_KEY")
        if not self.redis_url:
            missing.append("REDIS_URL")

        if missing:
            reason = (
                "Missing required production settings: "
                + ", ".join(missing)
            )
            if logger is not None:
                logger.error(reason)
            raise RuntimeError(reason)


settings = Settings()
