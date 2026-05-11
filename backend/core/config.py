from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "Northbound Control Tower"
    app_version: str = "0.1.0"
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://nct:nct_dev_password@postgres:5432/nct"
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    jwt_secret_key: str = Field(default="change-me-only-for-local-development", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=60, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    aws_default_region: str = Field(default="us-east-1", alias="AWS_DEFAULT_REGION")
    aws_scan_timeout_seconds: int = Field(default=300, alias="AWS_SCAN_TIMEOUT_SECONDS")
    ai_provider: str = Field(default="none", alias="AI_PROVIDER")
    ai_api_key: str | None = Field(default=None, alias="AI_API_KEY")
    ai_base_url: str | None = Field(default=None, alias="AI_BASE_URL")
    ai_model: str | None = Field(default=None, alias="AI_MODEL")
    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL")
    deepseek_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")
    backend_cors_origins_raw: str = Field(default="http://localhost:3000", alias="BACKEND_CORS_ORIGINS")

    @property
    def backend_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins_raw.split(",") if origin.strip()]

    @property
    def celery_broker(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def celery_backend(self) -> str:
        return self.celery_result_backend or self.redis_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
