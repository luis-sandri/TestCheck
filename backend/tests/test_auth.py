from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
import app.models as models  # noqa: F401 - registra as tabelas no metadata


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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


def test_register_login_and_logout(client: TestClient) -> None:
    registration = client.post(
        "/auth/register",
        json={
            "full_name": "Luís Sandri",
            "email": "luis@example.com",
            "password": "senha-segura-123",
        },
    )

    assert registration.status_code == 201
    assert registration.json()["email"] == "luis@example.com"
    assert client.get("/auth/me").status_code == 200

    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401

    login = client.post(
        "/auth/login",
        json={"email": "luis@example.com", "password": "senha-segura-123"},
    )
    assert login.status_code == 200
    assert login.json()["full_name"] == "Luís Sandri"


def test_login_rejects_wrong_password(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={
            "full_name": "André Murilo",
            "email": "andre@example.com",
            "password": "senha-segura-123",
        },
    )

    response = client.post(
        "/auth/login",
        json={"email": "andre@example.com", "password": "senha-errada"},
    )
    assert response.status_code == 401
