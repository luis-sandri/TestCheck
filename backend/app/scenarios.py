"""Importação de casos exportados pelo Zephyr e organização por folder."""

from __future__ import annotations

import csv
from io import StringIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .auth import get_current_user
from .database import get_db
from .models import Scenario, TestCase, User
from .schemas import ScenarioOutput, ZephyrImportOutput
from .test_cases import next_code


router = APIRouter(prefix="/scenarios", tags=["Cenários de teste"])

FIELD_ALIASES = {
    "folder": ("folder", "folder name", "folder path", "path", "test cycle folder"),
    "title": ("summary", "name", "title", "test case", "test case name"),
    "description": ("description", "objective", "objetivo"),
    "preconditions": ("precondition", "preconditions", "pré-condições", "pre condições"),
    "steps": ("test steps", "steps", "step", "passos", "test script"),
    "test_data": ("test data", "data", "dados de teste"),
    "expected_result": ("expected result", "expected results", "resultado esperado"),
    "approval_criteria": ("approval criteria", "acceptance criteria", "critério de aprovação", "criterio de aprovação"),
    "responsible_email": ("responsible email", "assignee email", "responsável", "responsavel", "assignee"),
}


def normalize(value: str) -> str:
    return " ".join(value.strip().casefold().replace("_", " ").split())


def clean_email(value: str, label: str) -> str:
    email = value.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Informe um e-mail válido para {label}.")
    return email


def value_from_row(row: dict[str, str], field: str) -> str:
    for alias in FIELD_ALIASES[field]:
        value = row.get(alias)
        if value:
            return value.strip()
    return ""


def serialize_scenario(scenario: Scenario) -> ScenarioOutput:
    return ScenarioOutput(
        id=scenario.id,
        name=scenario.name,
        zephyr_folder=scenario.zephyr_folder,
        reviewer_email=scenario.reviewer_email,
        supervisor_email=scenario.supervisor_email,
        test_case_count=len(scenario.test_cases),
        created_at=scenario.created_at,
    )


@router.get("", response_model=list[ScenarioOutput])
def list_scenarios(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ScenarioOutput]:
    scenarios = db.scalars(
        select(Scenario).options(selectinload(Scenario.test_cases)).order_by(Scenario.created_at.desc())
    ).all()
    return [serialize_scenario(scenario) for scenario in scenarios]


@router.post("/import-zephyr", response_model=ZephyrImportOutput, status_code=status.HTTP_201_CREATED)
async def import_zephyr_csv(
    file: UploadFile = File(...),
    reviewer_email: str = Form(...),
    supervisor_email: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ZephyrImportOutput:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Envie um arquivo CSV exportado pelo Zephyr.")
    reviewer_email = clean_email(reviewer_email, "revisor")
    supervisor_email = clean_email(supervisor_email, "supervisor")
    if supervisor_email == current_user.email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="O supervisor deve ser diferente de quem importou o cenário.")

    raw_content = await file.read()
    try:
        content = raw_content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="O CSV precisa estar codificado em UTF-8.") from error
    try:
        dialect = csv.Sniffer().sniff(content[:4096], delimiters=",;")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(StringIO(content), dialect=dialect)
    if not reader.fieldnames:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="O CSV não possui cabeçalho.")

    normalized_rows = []
    for index, row in enumerate(reader, start=2):
        normalized = {normalize(key): (value or "") for key, value in row.items() if key}
        title = value_from_row(normalized, "title")
        if not title:
            continue
        folder = value_from_row(normalized, "folder") or "Casos sem folder"
        responsible_email = value_from_row(normalized, "responsible_email") or current_user.email
        responsible_email = clean_email(responsible_email, f"responsável da linha {index}")
        if responsible_email == supervisor_email:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"O supervisor não pode ser o responsável da linha {index}.")
        normalized_rows.append((folder, title, responsible_email, normalized))
    if not normalized_rows:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nenhum caso com título foi encontrado no CSV.")

    imported_scenarios: dict[str, Scenario] = {}
    for folder, title, responsible_email, row in normalized_rows:
        scenario = imported_scenarios.get(folder)
        if scenario is None:
            scenario = db.scalar(
                select(Scenario).options(selectinload(Scenario.test_cases)).where(Scenario.zephyr_folder == folder)
            )
            if scenario is None:
                scenario = Scenario(
                    name=folder.split("/")[-1].strip() or folder,
                    zephyr_folder=folder,
                    reviewer_email=reviewer_email,
                    supervisor_email=supervisor_email,
                    created_by_id=current_user.id,
                )
                db.add(scenario)
                db.flush()
            else:
                scenario.reviewer_email = reviewer_email
                scenario.supervisor_email = supervisor_email
            imported_scenarios[folder] = scenario
        test_case = TestCase(
            code=next_code(db),
            title=title,
            scenario_id=scenario.id,
            author_id=current_user.id,
            responsible_email=responsible_email,
            description=value_from_row(row, "description"),
            preconditions=value_from_row(row, "preconditions"),
            steps=value_from_row(row, "steps"),
            test_data=value_from_row(row, "test_data"),
            expected_result=value_from_row(row, "expected_result"),
            approval_criteria=value_from_row(row, "approval_criteria"),
        )
        db.add(test_case)

    db.commit()
    persisted_scenarios = db.scalars(
        select(Scenario).options(selectinload(Scenario.test_cases)).where(Scenario.id.in_([scenario.id for scenario in imported_scenarios.values()]))
    ).all()
    return ZephyrImportOutput(imported_cases=len(normalized_rows), scenarios=[serialize_scenario(scenario) for scenario in persisted_scenarios])
