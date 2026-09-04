from app.database import Base
import app.models  # noqa: F401 - registra as tabelas no metadata
from sqlalchemy.orm import configure_mappers


def test_initial_schema_contains_the_mvp_entities() -> None:
    configure_mappers()
    assert set(Base.metadata.tables) == {
        "users",
        "test_cases",
        "audits",
        "audit_items",
        "nonconformities",
        "evidences",
    }
