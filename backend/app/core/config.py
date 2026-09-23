"""Application configuration, read from the environment or a local .env file."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "production"] = "development"
    app_url: str = "http://localhost:3000"
    public_api_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./databridge.db"

    secret_key: str = Field(default="dev-only-insecure-secret-replace-before-deploying", min_length=8)
    credentials_key: str = ""
    access_token_ttl_minutes: int = Field(default=720, ge=5)
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    allow_registration: bool = True

    http_timeout_seconds: float = Field(default=15, gt=0, le=120)
    max_response_mb: int = Field(default=5, ge=1, le=100)
    max_records_per_run: int = Field(default=5000, ge=1, le=100_000)
    retry_attempts: int = Field(default=3, ge=1, le=10)
    retry_base_delay_seconds: float = Field(default=0.5, ge=0, le=30)

    scheduler_enabled: bool = True
    scheduler_tick_seconds: int = Field(default=30, ge=1, le=3600)

    @field_validator("app_url", "public_api_url")
    @classmethod
    def _strip_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @model_validator(mode="after")
    def _guard(self) -> "Settings":
        if self.environment == "production":
            if "insecure" in self.secret_key or len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be a strong value in production")
            if not self.credentials_key:
                raise ValueError("CREDENTIALS_KEY is required in production")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production")
        return self

    @property
    def max_response_bytes(self) -> int:
        return self.max_response_mb * 1024 * 1024

    @property
    def debug_errors(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
