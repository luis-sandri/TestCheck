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
        json={"full_name": "Luís Sandri", "email": "luis@example.com", "password": "senha-segura-123", "organization_name": "Equipe Teste"},
    )
    assert response.status_code == 201


def test_create_update_list_and_delete_test_case(client: TestClient) -> None:
    authenticate(client)
    created = client.post("/test-cases", json={"title": "Login válido", "steps": "1. Informar credenciais", "reviewer_email": "revisor@example.com", "supervisor_email": "supervisor@example.com"})
    assert created.status_code == 201
    assert created.json()["code"] == "TC-001"
    assert created.json()["responsible_email"] == "luis@example.com"

    case_id = created.json()["id"]
    updated = client.put(
        f"/test-cases/{case_id}",
        json={"title": "Login válido", "steps": "1. Informar credenciais", "expected_result": "Acesso liberado", "responsible_email": "andre@example.com", "reviewer_email": "revisor@example.com", "supervisor_email": "supervisor@example.com"},
    )
    assert updated.status_code == 200
    assert updated.json()["expected_result"] == "Acesso liberado"
    assert updated.json()["responsible_email"] == "andre@example.com"
    listed = client.get("/test-cases")
    assert listed.headers["cache-control"] == "no-store, max-age=0"
    assert len(listed.json()) == 1
    assert client.delete(f"/test-cases/{case_id}").status_code == 204
    assert client.get("/test-cases").json() == []


def test_run_automated_audit_generates_nonconformities(client: TestClient) -> None:
    authenticate(client)
    created = client.post(
        "/test-cases",
        json={
                "title": "Login válido",
                "steps": "1. Informar credenciais",
                "expected_result": "Acesso liberado",
                "reviewer_email": "luis@example.com",
                "supervisor_email": "supervisor@example.com",
        },
    )
    audit = client.post("/audits", json={"test_case_id": created.json()["id"]})

    assert audit.status_code == 201
    assert audit.json()["status"] == "DRAFT"
    items_by_code = {item["checklist_code"]: item for item in audit.json()["items"]}
    assert items_by_code["STEPS"]["field_value"] == "1. Informar credenciais"
    assert items_by_code["EXPECTED_RESULT"]["field_value"] == "Acesso liberado"
    assert items_by_code["OBJECTIVE"]["field_value"] is None
    review = client.post(
        f"/audits/{audit.json()['id']}/review",
        json={
            "items": [
                {
                    "checklist_code": item["checklist_code"],
                    "result": item["suggested_result"],
                    "priority": "MEDIUM" if item["suggested_result"] == "NONCONFORMING" else None,
                }
                for item in audit.json()["items"]
            ]
        },
    )
    assert review.status_code == 200
    assert review.json()["status"] == "COMPLETED"
    assert review.json()["adherence_percentage"] == 33
    assert review.json()["original_adherence_percentage"] == 33
    assert review.json()["nonconformity_count"] == 4
    assert len(client.get("/audits").json()) == 1

    nonconformity = client.get("/nonconformities").json()[0]
    evidence = client.post(
        f"/nonconformities/{nonconformity['id']}/evidences",
        json={"description": "O campo foi preenchido e revisado."},
    )
    assert evidence.status_code == 200
    assert evidence.json()["status"] == "WAITING_VALIDATION"
    assert evidence.json()["evidences"][0]["status"] == "SUBMITTED"

    reviewed = client.post(
        f"/nonconformities/{nonconformity['id']}/review",
        json={"evidence_id": evidence.json()["evidences"][0]["id"], "approved": True},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "RESOLVED"

    refreshed_audit = client.get("/audits").json()[0]
    assert refreshed_audit["adherence_percentage"] == 50
    assert refreshed_audit["original_adherence_percentage"] == 33


def test_numbering_and_data_are_scoped_by_scenario_and_organization(client: TestClient) -> None:
    authenticate(client)
    general_one = client.post("/test-cases", json={"title": "Geral 1", "reviewer_email": "revisor@example.com", "supervisor_email": "supervisor@example.com"})
    general_two = client.post("/test-cases", json={"title": "Geral 2", "reviewer_email": "revisor@example.com", "supervisor_email": "supervisor@example.com"})
    assert general_one.json()["code"] == "TC-001"
    assert general_two.json()["code"] == "TC-002"

    second_user = TestClient(app)
    registration = second_user.post("/auth/register", json={"full_name": "André Murilo", "email": "andre@example.com", "password": "senha-segura-123", "organization_name": "Outra Equipe"})
    assert registration.status_code == 201
    isolated_case = second_user.post("/test-cases", json={"title": "Caso isolado", "reviewer_email": "revisor@example.com", "supervisor_email": "supervisor@example.com"})
    assert isolated_case.status_code == 201
    assert isolated_case.json()["code"] == "TC-001"
    assert len(client.get("/test-cases").json()) == 2
    assert len(second_user.get("/test-cases").json()) == 1
    second_user.close()
