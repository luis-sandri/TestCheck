from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TestCheck API"
    database_url: str = (
        "postgresql+psycopg://testcheck:testcheck@localhost:5432/testcheck"
    )
    frontend_origin: str = "http://localhost:5173"
    session_cookie_name: str = "testcheck_session"

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

