from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TestCheck API"
    database_url: str = (
        "postgresql+psycopg://testcheck:testcheck@localhost:5432/testcheck"
    )
    frontend_origin: str = "http://localhost:5173"
    app_url: str = "http://localhost:5173"
    resend_api_key: str | None = None
    email_from: str = "TestCheck <onboarding@resend.dev>"
    session_cookie_name: str = "testcheck_session"
    session_duration_hours: int = 168

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        """Adapta a URL padrão do Neon para o driver instalado na API."""
        if value.startswith("postgresql+psycopg://"):
            return value
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
