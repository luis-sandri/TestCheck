from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .auth import get_current_user
from .database import get_db
from .models import TestCase, User, UserRole
from .schemas import TestCaseInput, TestCaseOutput


router = APIRouter(prefix="/test-cases", tags=["Casos de teste"])


def serialize_case(test_case: TestCase) -> TestCaseOutput:
    return TestCaseOutput(
        id=test_case.id,
        code=test_case.code,
        title=test_case.title,
        description=test_case.description,
        preconditions=test_case.preconditions,
        steps=test_case.steps,
        test_data=test_case.test_data,
        expected_result=test_case.expected_result,
        approval_criteria=test_case.approval_criteria,
        author_id=test_case.author_id,
        author_name=test_case.author.full_name,
        responsible_email=test_case.responsible_email or test_case.author.email,
        created_at=test_case.created_at,
        updated_at=test_case.updated_at,
    )


def get_case_or_404(case_id: str, db: Session) -> TestCase:
    test_case = db.scalar(
        select(TestCase).options(selectinload(TestCase.author)).where(TestCase.id == case_id)
    )
    if test_case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caso de teste não encontrado.")
    return test_case


def ensure_can_edit(test_case: TestCase, user: User) -> None:
    if test_case.author_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não pode alterar este caso.")


def next_code(db: Session) -> str:
    codes = db.scalars(select(TestCase.code)).all()
    used_numbers = [int(code.removeprefix("TC-")) for code in codes if code.startswith("TC-") and code[3:].isdigit()]
    return f"TC-{(max(used_numbers, default=0) + 1):03d}"


@router.get("", response_model=list[TestCaseOutput])
def list_test_cases(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[TestCaseOutput]:
    cases = db.scalars(
        select(TestCase).options(selectinload(TestCase.author)).order_by(TestCase.created_at.desc())
    ).all()
    return [serialize_case(test_case) for test_case in cases]


@router.post("", response_model=TestCaseOutput, status_code=status.HTTP_201_CREATED)
def create_test_case(
    payload: TestCaseInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestCaseOutput:
    values = payload.model_dump()
    values["responsible_email"] = values["responsible_email"] or current_user.email
    test_case = TestCase(code=next_code(db), author_id=current_user.id, **values)
    db.add(test_case)
    db.commit()
    db.refresh(test_case)
    return serialize_case(get_case_or_404(test_case.id, db))


@router.get("/{case_id}", response_model=TestCaseOutput)
def get_test_case(
    case_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TestCaseOutput:
    return serialize_case(get_case_or_404(case_id, db))


@router.put("/{case_id}", response_model=TestCaseOutput)
def update_test_case(
    case_id: str,
    payload: TestCaseInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestCaseOutput:
    test_case = get_case_or_404(case_id, db)
    ensure_can_edit(test_case, current_user)
    values = payload.model_dump()
    if not values["responsible_email"]:
        values["responsible_email"] = test_case.responsible_email or test_case.author.email
    for field, value in values.items():
        setattr(test_case, field, value)
    db.commit()
    return serialize_case(get_case_or_404(case_id, db))


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    test_case = get_case_or_404(case_id, db)
    ensure_can_edit(test_case, current_user)
    if test_case.audits:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este caso já possui auditorias e não pode ser excluído.",
        )
    db.delete(test_case)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
