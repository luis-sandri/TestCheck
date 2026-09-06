"""Execução da auditoria automatizada dos artefatos de caso de teste."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .auth import get_current_user
from .database import get_db
from .models import (
    Audit,
    AuditItem,
    AuditStatus,
    ChecklistResult,
    Nonconformity,
    NonconformitySeverity,
    Notification,
    NotificationType,
    TestCase,
    User,
)
from .schemas import AuditItemOutput, AuditOutput, AuditStartInput


router = APIRouter(prefix="/audits", tags=["Auditorias"])


# Os critérios correspondem aos campos mínimos de um caso de teste bem documentado.
CHECKLIST = (
    ("OBJECTIVE", "Objetivo do teste", "description", NonconformitySeverity.LOW),
    ("PRECONDITIONS", "Pré-condições", "preconditions", NonconformitySeverity.MEDIUM),
    ("STEPS", "Passos de teste", "steps", NonconformitySeverity.HIGH),
    ("TEST_DATA", "Dados de teste", "test_data", NonconformitySeverity.MEDIUM),
    ("EXPECTED_RESULT", "Resultado esperado", "expected_result", NonconformitySeverity.HIGH),
    ("APPROVAL_CRITERIA", "Critério de aprovação", "approval_criteria", NonconformitySeverity.MEDIUM),
)


def get_test_case_or_404(case_id: str, db: Session) -> TestCase:
    test_case = db.scalar(
        select(TestCase).options(selectinload(TestCase.author)).where(TestCase.id == case_id)
    )
    if test_case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caso de teste não encontrado.")
    return test_case


def next_nc_code(db: Session) -> str:
    codes = db.scalars(select(Nonconformity.code)).all()
    numbers = [int(code.removeprefix("NC-")) for code in codes if code.startswith("NC-") and code[3:].isdigit()]
    return f"NC-{(max(numbers, default=0) + 1):03d}"


def serialize_audit(audit: Audit) -> AuditOutput:
    return AuditOutput(
        id=audit.id,
        test_case_id=audit.test_case_id,
        test_case_code=audit.test_case.code,
        test_case_title=audit.test_case.title,
        auditor_name=audit.auditor.full_name,
        status=audit.status,
        adherence_percentage=audit.adherence_percentage,
        nonconformity_count=sum(item.result == ChecklistResult.NONCONFORMING for item in audit.items),
        items=[
            AuditItemOutput(
                checklist_code=item.checklist_code,
                checklist_label=item.checklist_label,
                result=item.result,
                note=item.note,
            )
            for item in audit.items
        ],
        created_at=audit.created_at,
        completed_at=audit.completed_at,
    )


@router.get("", response_model=list[AuditOutput])
def list_audits(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AuditOutput]:
    audits = db.scalars(
        select(Audit)
        .options(selectinload(Audit.test_case), selectinload(Audit.auditor), selectinload(Audit.items))
        .order_by(Audit.created_at.desc())
    ).all()
    return [serialize_audit(audit) for audit in audits]


@router.post("", response_model=AuditOutput, status_code=status.HTTP_201_CREATED)
def run_audit(
    payload: AuditStartInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditOutput:
    test_case = get_test_case_or_404(payload.test_case_id, db)
    completed_at = datetime.now(UTC)
    audit = Audit(
        test_case_id=test_case.id,
        auditor_id=current_user.id,
        status=AuditStatus.COMPLETED,
        completed_at=completed_at,
    )
    db.add(audit)
    db.flush()

    assignee_email = test_case.responsible_email or test_case.author.email
    assignee = db.scalar(select(User).where(User.email == assignee_email))
    conforming_items = 0

    for position, (code, label, field, severity) in enumerate(CHECKLIST, start=1):
        is_filled = bool((getattr(test_case, field) or "").strip())
        result = ChecklistResult.CONFORMING if is_filled else ChecklistResult.NONCONFORMING
        item = AuditItem(
            audit_id=audit.id,
            checklist_code=code,
            checklist_label=label,
            position=position,
            result=result,
            note=None if is_filled else f"{label} não foi informado no caso de teste.",
        )
        db.add(item)
        db.flush()

        if is_filled:
            conforming_items += 1
            continue

        nonconformity = Nonconformity(
            code=next_nc_code(db),
            test_case_id=test_case.id,
            audit_item_id=item.id,
            assignee_id=assignee.id if assignee else None,
            assignee_email=assignee_email,
            description=f"{label} ausente no caso {test_case.code}: {test_case.title}.",
            severity=severity,
            due_date=(completed_at + timedelta(days=7)).date(),
        )
        db.add(nonconformity)
        db.flush()
        db.add(
            Notification(
                recipient_id=assignee.id if assignee else None,
                recipient_email=assignee_email,
                nonconformity_id=nonconformity.id,
                notification_type=NotificationType.NONCONFORMITY_ASSIGNED,
                title=f"{nonconformity.code} atribuída a você",
                message=f"A auditoria do caso {test_case.code} identificou: {label} não informado.",
            )
        )

    audit.adherence_percentage = round((conforming_items / len(CHECKLIST)) * 100)
    db.commit()
    db.refresh(audit)
    persisted_audit = db.scalar(
        select(Audit)
        .options(selectinload(Audit.test_case), selectinload(Audit.auditor), selectinload(Audit.items))
        .where(Audit.id == audit.id)
    )
    assert persisted_audit is not None
    return serialize_audit(persisted_audit)
