"""Application settings, loaded from environment variables (never hard-coded secrets)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "staging", "production"]

#: HttpOnly cookie carrying the web refresh token (path-scoped to the auth endpoints).
REFRESH_COOKIE = "nirnoy_rt"

_INSECURE_MARKERS = ("change-me", "changeme", "dev-only", "insecure")


class Settings(BaseSettings):
    # Repo-root .env first (shared with docker-compose), then a service-local override.
    model_config = SettingsConfigDict(
        env_file=("../../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Nirnoy Diagnostics API"
    environment: Environment = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # Infrastructure
    database_url: str = "postgresql+asyncpg://nirnoy:nirnoy@localhost:5432/nirnoy"
    database_pool_size: int = 10
    database_max_overflow: int = 10
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None

    # Object storage (S3-compatible: SeaweedFS locally, S3 in production)
    s3_endpoint_url: str | None = "http://localhost:9000"
    s3_region: str = "ap-southeast-1"
    s3_access_key: SecretStr = SecretStr("")
    s3_secret_key: SecretStr = SecretStr("")
    s3_bucket_prefix: str = "nirnoy"
    #: Server-side encryption for private objects; empty disables it (local S3 emulators).
    s3_server_side_encryption: str = "AES256"

    # Tokens
    jwt_secret: SecretStr = Field(default=SecretStr(""))
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_issuer: str = "nirnoy-api"
    jwt_audience: str = "nirnoy-clients"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_days: int = 30
    refresh_cookie_secure: bool = True
    refresh_cookie_path: str = "/api/v1/auth"

    # OTP
    otp_hmac_secret: SecretStr = Field(default=SecretStr(""))
    otp_length: int = 6
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 5
    otp_send_limit_per_phone: int = 3
    otp_send_limit_per_ip: int = 10
    otp_send_window_seconds: int = 900

    # Login protection
    login_attempt_limit: int = 5
    login_attempt_window_seconds: int = 900
    staff_two_factor_required: bool = True

    # Providers
    sms_provider: Literal["console", "disabled"] = "console"

    # HTTP
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174"]

    # Observability
    sentry_dsn: str | None = None

    @field_validator("database_url")
    @classmethod
    def _async_driver(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @model_validator(mode="after")
    def _validate_secrets(self) -> Settings:
        for name in ("jwt_secret", "otp_hmac_secret"):
            value: SecretStr = getattr(self, name)
            raw = value.get_secret_value()
            if len(raw) < 32:
                raise ValueError(f"{name.upper()} must be set and at least 32 characters")
            if self.is_production_like and any(m in raw.lower() for m in _INSECURE_MARKERS):
                raise ValueError(f"{name.upper()} uses a placeholder value in {self.environment}")
        if self.is_production_like:
            if not self.refresh_cookie_secure:
                raise ValueError("REFRESH_COOKIE_SECURE must be true outside development")
            if self.sms_provider == "console":
                raise ValueError("Console SMS provider is not allowed outside development/test")
        return self

    @property
    def is_production_like(self) -> bool:
        return self.environment in ("staging", "production")

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
