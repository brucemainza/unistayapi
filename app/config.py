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


settings = Settings()

if settings.environment == "production" and not settings.google_maps_server_key:
    raise RuntimeError("GOOGLE_MAPS_SERVER_KEY is required in production")

if settings.environment == "production" and not settings.redis_url:
    raise RuntimeError("REDIS_URL is required in production")
