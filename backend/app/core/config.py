"""Application settings, loaded from environment variables and validated at startup."""

from functools import lru_cache
from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

MIN_PRODUCTION_TOKEN_LENGTH = 16
PLACEHOLDER_TOKENS = {"change-me", "changeme", "secret", "token"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # "KEY=" in .env means "not set"
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: str = "sqlite:///./data/fgr.db"
    api_token: SecretStr = SecretStr("")

    default_timezone: str = "Asia/Jakarta"
    steam_region: str = Field(default="ID", min_length=2, max_length=2)
    steam_currency: str = Field(default="IDR", min_length=3, max_length=3)

    giveaway_scan_interval_minutes: int = Field(default=30, gt=0)
    price_scan_interval_minutes: int = Field(default=360, gt=0)
    wishlist_sync_interval_minutes: int = Field(default=1440, gt=0)
    # Comma-separated in the environment, e.g. "1440,360,60,30".
    reminder_offsets_minutes: Annotated[list[int], NoDecode] = [1440, 360, 60, 30]

    http_timeout_seconds: float = Field(default=15.0, gt=0)
    user_agent: str = "FreeGameRadar/0.1"

    steam_web_api_key: SecretStr | None = None
    telegram_bot_token: SecretStr | None = None
    telegram_chat_id: str | None = None
    itad_api_key: SecretStr | None = None

    @field_validator("reminder_offsets_minutes", mode="before")
    @classmethod
    def _parse_offsets(cls, value: object) -> object:
        if isinstance(value, str):
            return [int(part) for part in value.split(",") if part.strip()]
        return value

    @field_validator("reminder_offsets_minutes")
    @classmethod
    def _check_offsets(cls, value: list[int]) -> list[int]:
        if any(v <= 0 for v in value):
            raise ValueError("reminder offsets must be positive minutes")
        return sorted(set(value), reverse=True)

    @field_validator("default_timezone")
    @classmethod
    def _check_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown IANA timezone: {value!r}") from exc
        return value

    @field_validator("steam_region", "steam_currency")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def _check_production_secrets(self) -> Self:
        if self.app_env == "production":
            token = self.api_token.get_secret_value()
            if len(token) < MIN_PRODUCTION_TOKEN_LENGTH or token.lower() in PLACEHOLDER_TOKENS:
                raise ValueError(
                    f"API_TOKEN must be set to a real secret "
                    f"(>= {MIN_PRODUCTION_TOKEN_LENGTH} chars) when APP_ENV=production"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
