from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Northbound Control Tower"
    app_version: str = "0.1.0"
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://nct:nct_dev_password@postgres:5432/nct"
    redis_url: str = "redis://redis:6379/0"
    backend_cors_origins_raw: str = Field(default="http://localhost:3000", alias="BACKEND_CORS_ORIGINS")

    @property
    def backend_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins_raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
