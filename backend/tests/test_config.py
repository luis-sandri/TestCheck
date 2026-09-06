from app.config import Settings


def test_neon_database_url_uses_installed_driver() -> None:
    settings = Settings(database_url="postgresql://user:secret@host.neon.tech/db")

    assert settings.database_url == "postgresql+psycopg://user:secret@host.neon.tech/db"
