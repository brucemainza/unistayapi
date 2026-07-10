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


settings = Settings()
