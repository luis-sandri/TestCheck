from __future__ import annotations

from collections.abc import Generator
from io import BytesIO
import json

from fastapi.testclient import TestClient
from openpyxl import Workbook
import pytest
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
        registration = test_client.post(
            "/auth/register",
            json={"full_name": "Luís Sandri", "email": "luis@example.com", "password": "senha-segura-123"},
        )
        assert registration.status_code == 201
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)


def import_file(client: TestClient, filename: str, content: bytes, owner_map: dict[str, str] | None = None):
    return client.post(
        "/scenarios/import-zephyr",
        data={
            "reviewer_email": "revisor@example.com",
            "supervisor_email": "supervisor@example.com",
            "owner_email_map": json.dumps(owner_map or {}),
        },
        files={"file": (filename, content, "application/octet-stream")},
    )


def test_xml_export_requests_owner_mapping_then_imports(client: TestClient) -> None:
    xml = b"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
    <project><folders/><testCases><testCase key=\"SCRUM-T1\">
      <name>Login valido</name><objective>Validar acesso</objective><precondition>Usuario cadastrado</precondition>
      <owner>712020:13f64522-512c-4810-8786-406a05679ff7</owner>
      <testScript type=\"steps\"><steps><step index=\"0\"><description>Informar credenciais</description><testData>usuario valido</testData><expectedResult>Acesso liberado</expectedResult></step></steps></testScript>
    </testCase></testCases></project>"""

    mapping_needed = import_file(client, "atm-exporter.xml", xml)
    assert mapping_needed.status_code == 422
    detail = mapping_needed.json()["detail"]
    assert detail["code"] == "OWNER_EMAIL_REQUIRED"
    assert detail["owners"][0]["identifier"] == "712020:13f64522-512c-4810-8786-406a05679ff7"

    imported = import_file(
        client,
        "atm-exporter.xml",
        xml,
        {"712020:13f64522-512c-4810-8786-406a05679ff7": "andre@example.com"},
    )
    assert imported.status_code == 201
    assert imported.json()["imported_cases"] == 1
    case = client.get("/test-cases").json()[0]
    assert case["title"] == "Login valido"
    assert case["zephyr_key"] == "SCRUM-T1"
    assert case["responsible_email"] == "andre@example.com"
    assert case["description"] == "Validar acesso"
    assert case["steps"] == "Informar credenciais"
    assert case["expected_result"] == "Acesso liberado"


def test_xlsx_export_groups_repeated_steps_and_uses_folder(client: TestClient) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append([
        "Key", "Name", "Folder", "Owner", "Objective", "Precondition",
        "Test Script (Step-by-Step) - Step", "Test Script (Step-by-Step) - Test Data",
        "Test Script (Step-by-Step) - Expected Result",
    ])
    sheet.append(["SCRUM-T2", "Cadastro", "Regressao/Conta", "andre@example.com", "Criar conta", "Pagina aberta", "Preencher formulario", "nome valido", "Conta criada"])
    sheet.append(["SCRUM-T2", "Cadastro", "Regressao/Conta", "andre@example.com", "Criar conta", "Pagina aberta", "Enviar formulario", "", "Confirmacao exibida"])
    output = BytesIO()
    workbook.save(output)

    imported = import_file(client, "atm-exporter.xlsx", output.getvalue())
    assert imported.status_code == 201
    assert imported.json()["imported_cases"] == 1
    assert imported.json()["scenarios"][0]["zephyr_folder"] == "Regressao/Conta"
    case = client.get("/test-cases").json()[0]
    assert case["responsible_email"] == "andre@example.com"
    assert case["steps"] == "1. Preencher formulario\n2. Enviar formulario"
    assert case["test_data"] == "nome valido"
    assert case["expected_result"] == "1. Conta criada\n2. Confirmacao exibida"
