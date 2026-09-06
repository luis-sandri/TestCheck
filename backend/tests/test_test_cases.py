from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models as models  # noqa: F401
from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    test_session = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(test_engine)

    def override_db() -> Generator[Session, None, None]:
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)


def authenticate(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"full_name": "Luís Sandri", "email": "luis@example.com", "password": "senha-segura-123"},
    )
    assert response.status_code == 201


def test_create_update_list_and_delete_test_case(client: TestClient) -> None:
    authenticate(client)
    created = client.post("/test-cases", json={"title": "Login válido", "steps": "1. Informar credenciais"})
    assert created.status_code == 201
    assert created.json()["code"] == "TC-001"
    assert created.json()["responsible_email"] == "luis@example.com"

    case_id = created.json()["id"]
    updated = client.put(
        f"/test-cases/{case_id}",
        json={"title": "Login válido", "steps": "1. Informar credenciais", "expected_result": "Acesso liberado", "responsible_email": "andre@example.com"},
    )
    assert updated.status_code == 200
    assert updated.json()["expected_result"] == "Acesso liberado"
    assert updated.json()["responsible_email"] == "andre@example.com"
    assert len(client.get("/test-cases").json()) == 1
    assert client.delete(f"/test-cases/{case_id}").status_code == 204
    assert client.get("/test-cases").json() == []
