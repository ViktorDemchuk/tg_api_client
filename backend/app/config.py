from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Database ──
    database_url: str = "postgresql+psycopg://tg_client:change-me@postgres:5432/tg_client"
    
    # ── API ──
    backend_cors_origins: str = "http://localhost:3000,http://localhost:8080"
    api_root_path: str = ""
    log_level: str = "INFO"

    # ── JWT ──
    jwt_secret_key: str = "change-me-generate-a-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # ── Session encryption ──
    session_encryption_key: str = ""  # Required Fernet key for stored Telegram sessions

    # ── Telegram (app-level, shared) ──
    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    telegram_device_model: str = "Desktop"
    telegram_system_version: str = "Windows 10"
    telegram_app_version: str = "4.16.8"

    # ── Limits ──
    max_accounts_per_user: int = 5
    sync_interval_seconds: int = 120
    messages_per_chat: int = 100

    # ── Admin bootstrap ──
    admin_email: str = "admin@localhost"
    admin_password: str = "change-me"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @field_validator("telegram_api_id", "telegram_api_hash", mode="before")
    @classmethod
    def empty_string_as_none(cls, value: object) -> object:
        if value == "":
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
