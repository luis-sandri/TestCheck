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
            json={"full_name": "Luís Sandri", "email": "luis@example.com", "password": "senha-segura-123", "organization_name": "Equipe Teste"},
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
        files={"files": (filename, content, "application/octet-stream")},
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


def test_import_accepts_multiple_files_and_keeps_case_numbers_per_folder(client: TestClient) -> None:
    first = b"Key,Name,Folder,Owner\nA-1,Login,Regressao/Login,andre@example.com\n"
    second = b"Key,Name,Folder,Owner\nB-1,Cadastro,Regressao/Cadastro,andre@example.com\nB-2,Consulta,Regressao/Cadastro,andre@example.com\n"
    imported = client.post(
        "/scenarios/import-zephyr",
        data={"reviewer_email": "revisor@example.com", "supervisor_email": "supervisor@example.com", "owner_email_map": "{}"},
        files=[("files", ("login.csv", first, "text/csv")), ("files", ("cadastro.csv", second, "text/csv"))],
    )
    assert imported.status_code == 201
    assert imported.json()["imported_cases"] == 3
    assert len(imported.json()["scenarios"]) == 2
    cases = {case["title"]: case for case in client.get("/test-cases").json()}
    assert cases["Login"]["code"] == "TC-001"
    assert cases["Cadastro"]["code"] == "TC-001"
    assert cases["Consulta"]["code"] == "TC-002"


def test_bulk_import_and_manual_edit_keep_numbering_independent_per_scenario(client: TestClient) -> None:
    """Regressão: lote Zephyr, criação manual e edição não misturam as numerações."""
    imported = client.post(
        "/scenarios/import-zephyr",
        data={
            "reviewer_email": "revisor@example.com",
            "supervisor_email": "supervisor@example.com",
            "owner_email_map": "{}",
        },
        files=[
            (
                "files",
                (
                    "login.csv",
                    b"Key,Name,Folder,Owner\nLOG-1,Login valido,Regressao/Login,andre@example.com\nLOG-2,Login invalido,Regressao/Login,andre@example.com\n",
                    "text/csv",
                ),
            ),
            (
                "files",
                (
                    "conta.csv",
                    b"Key,Name,Folder,Owner\nACC-1,Criar conta,Regressao/Conta,andre@example.com\n",
                    "text/csv",
                ),
            ),
        ],
    )

    assert imported.status_code == 201
    assert imported.json()["imported_cases"] == 3
    scenarios = {scenario["zephyr_folder"]: scenario for scenario in imported.json()["scenarios"]}
    login_scenario = scenarios["Regressao/Login"]
    assert scenarios["Regressao/Conta"]["test_case_count"] == 1

    manual_in_scenario = client.post(
        "/test-cases",
        json={"title": "Recuperar senha", "scenario_id": login_scenario["id"]},
    )
    assert manual_in_scenario.status_code == 201
    assert manual_in_scenario.json()["code"] == "TC-003"
    assert manual_in_scenario.json()["reviewer_email"] == "revisor@example.com"
    assert manual_in_scenario.json()["supervisor_email"] == "supervisor@example.com"

    general_case = client.post(
        "/test-cases",
        json={
            "title": "Caso geral",
            "reviewer_email": "revisor@example.com",
            "supervisor_email": "supervisor@example.com",
        },
    )
    assert general_case.status_code == 201
    assert general_case.json()["code"] == "TC-001"
    assert general_case.json()["scenario_id"] is None

    moved_case = client.put(
        f"/test-cases/{general_case.json()['id']}",
        json={"title": "Caso geral", "scenario_id": login_scenario["id"]},
    )
    assert moved_case.status_code == 200
    assert moved_case.json()["code"] == "TC-004"
    assert moved_case.json()["scenario_id"] == login_scenario["id"]


def test_organization_switching_isolates_imported_and_manual_data(client: TestClient) -> None:
    """Regressão: trocar de organização só exibe e permite alterar dados do espaço ativo."""
    user = client.get("/auth/me").json()
    organization_a = user["active_organization"]["id"]
    imported = import_file(
        client,
        "conta.csv",
        b"Key,Name,Folder,Owner\nACC-1,Criar conta,Regressao/Conta,andre@example.com\n",
    )
    assert imported.status_code == 201
    case_from_a = client.get("/test-cases").json()[0]

    organization_b = client.post("/organizations", json={"name": "Equipe B"})
    assert organization_b.status_code == 201
    organization_b_id = organization_b.json()["active_organization"]["id"]
    assert client.get("/test-cases").json() == []
    assert client.get("/scenarios").json() == []
    assert client.put(f"/test-cases/{case_from_a['id']}", json={"title": "Não deve alterar"}).status_code == 404

    case_from_b = client.post(
        "/test-cases",
        json={
            "title": "Caso da Equipe B",
            "reviewer_email": "revisor@example.com",
            "supervisor_email": "supervisor@example.com",
        },
    )
    assert case_from_b.status_code == 201
    assert case_from_b.json()["code"] == "TC-001"

    switched_back = client.post("/organizations/select", json={"organization_id": organization_a})
    assert switched_back.status_code == 200
    assert switched_back.json()["active_organization"]["id"] == organization_a
    assert [case["title"] for case in client.get("/test-cases").json()] == ["Criar conta"]

    member = TestClient(app)
    joined = member.post(
        "/auth/register",
        json={
            "full_name": "André Murilo",
            "email": "andre@example.com",
            "password": "senha-segura-123",
            "organization_id": organization_a,
        },
    )
    assert joined.status_code == 201
    assert [case["title"] for case in member.get("/test-cases").json()] == ["Criar conta"]
    assert member.post("/organizations/select", json={"organization_id": organization_b_id}).status_code == 403
    member.close()
