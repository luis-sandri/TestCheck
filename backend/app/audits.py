"""Auditoria assistida: a automação sugere e o revisor decide o resultado."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .auth import get_current_user
from .database import get_db
from .email_service import send_notification_email
from .models import (
    Audit,
    AuditItem,
    AuditStatus,
    ChecklistResult,
    Nonconformity,
    NonconformityHistory,
    NonconformitySeverity,
    Notification,
    NotificationType,
    TestCase,
    User,
)
from .schemas import AuditItemOutput, AuditOutput, AuditReviewInput, AuditStartInput
from .sla import add_business_days, target_for


router = APIRouter(prefix="/audits", tags=["Auditorias"])

CHECKLIST = (
    ("OBJECTIVE", "Objetivo do teste", "description"),
    ("PRECONDITIONS", "Pré-condições", "preconditions"),
    ("STEPS", "Passos de teste", "steps"),
    ("TEST_DATA", "Dados de teste", "test_data"),
    ("EXPECTED_RESULT", "Resultado esperado", "expected_result"),
    ("APPROVAL_CRITERIA", "Critério de aprovação", "approval_criteria"),
)

def audit_query():
    return select(Audit).options(
        selectinload(Audit.test_case).selectinload(TestCase.author),
        selectinload(Audit.test_case).selectinload(TestCase.scenario),
        selectinload(Audit.auditor),
        selectinload(Audit.items),
    )


def get_test_case_or_404(case_id: str, db: Session) -> TestCase:
    test_case = db.scalar(
        select(TestCase)
        .options(selectinload(TestCase.author), selectinload(TestCase.scenario))
        .where(TestCase.id == case_id)
    )
    if test_case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caso de teste não encontrado.")
    return test_case


def get_audit_or_404(audit_id: str, db: Session) -> Audit:
    audit = db.scalar(audit_query().where(Audit.id == audit_id))
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auditoria não encontrada.")
    return audit


def can_review(audit: Audit, user: User) -> bool:
    scenario = audit.test_case.scenario
    reviewer_email = scenario.reviewer_email if scenario else audit.test_case.reviewer_email
    return reviewer_email == user.email if reviewer_email else audit.auditor_id == user.id


def supervisor_email_for(audit: Audit) -> str | None:
    scenario = audit.test_case.scenario
    return scenario.supervisor_email if scenario else audit.test_case.supervisor_email


def next_nc_code(db: Session) -> str:
    codes = db.scalars(select(Nonconformity.code)).all()
    numbers = [int(code.removeprefix("NC-")) for code in codes if code.startswith("NC-") and code[3:].isdigit()]
    return f"NC-{(max(numbers, default=0) + 1):03d}"


def serialize_audit(audit: Audit, user: User) -> AuditOutput:
    return AuditOutput(
        id=audit.id,
        test_case_id=audit.test_case_id,
        test_case_code=audit.test_case.code,
        test_case_title=audit.test_case.title,
        scenario_id=audit.test_case.scenario_id,
        scenario_name=audit.test_case.scenario.name if audit.test_case.scenario else None,
        auditor_name=audit.auditor.full_name,
        status=audit.status,
        adherence_percentage=audit.adherence_percentage,
        nonconformity_count=sum(item.final_result == ChecklistResult.NONCONFORMING for item in audit.items),
        items=[
            AuditItemOutput(
                checklist_code=item.checklist_code,
                checklist_label=item.checklist_label,
                result=item.final_result or item.suggested_result or item.result,
                suggested_result=item.suggested_result or item.result,
                final_result=item.final_result,
                note=item.note,
            )
            for item in audit.items
        ],
        created_at=audit.created_at,
        completed_at=audit.completed_at,
        can_review=audit.status == AuditStatus.DRAFT and can_review(audit, user),
    )


@router.get("", response_model=list[AuditOutput])
def list_audits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AuditOutput]:
    audits = db.scalars(audit_query().order_by(Audit.created_at.desc())).all()
    return [serialize_audit(audit, current_user) for audit in audits]


@router.post("", response_model=AuditOutput, status_code=status.HTTP_201_CREATED)
def run_audit(
    payload: AuditStartInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditOutput:
    test_case = get_test_case_or_404(payload.test_case_id, db)
    pending_audit = db.scalar(
        select(Audit).where(
            Audit.test_case_id == test_case.id,
            Audit.status == AuditStatus.DRAFT,
        )
    )
    if pending_audit is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este caso já possui uma auditoria aguardando revisão.",
        )
    audit = Audit(test_case_id=test_case.id, auditor_id=current_user.id, status=AuditStatus.DRAFT)
    db.add(audit)
    db.flush()

    for position, (code, label, field) in enumerate(CHECKLIST, start=1):
        is_filled = bool((getattr(test_case, field) or "").strip())
        suggestion = ChecklistResult.CONFORMING if is_filled else ChecklistResult.NONCONFORMING
        db.add(
            AuditItem(
                audit_id=audit.id,
                checklist_code=code,
                checklist_label=label,
                position=position,
                result=suggestion,
                suggested_result=suggestion,
                final_result=None,
                note=None if is_filled else f"Sugestão automática: {label} não foi informado no caso de teste.",
            )
        )

    db.commit()
    return serialize_audit(get_audit_or_404(audit.id, db), current_user)


@router.post("/{audit_id}/review", response_model=AuditOutput)
def review_audit(
    audit_id: str,
    payload: AuditReviewInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditOutput:
    audit = get_audit_or_404(audit_id, db)
    if audit.status != AuditStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta auditoria já foi revisada.")
    if not can_review(audit, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Somente o revisor definido para o caso pode finalizar a auditoria.")

    results_by_code = {item.checklist_code: item for item in payload.items}
    expected_codes = {item.checklist_code for item in audit.items}
    if set(results_by_code) != expected_codes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Revise todos os itens do checklist antes de finalizar.")
    supervisor_email = supervisor_email_for(audit)
    if not supervisor_email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Defina um supervisor no caso ou no cenário antes de finalizar a auditoria.")
    if supervisor_email in {audit.test_case.author.email, audit.test_case.responsible_email, audit.auditor.email}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="O supervisor deve ser diferente do autor, responsável e auditor do caso.")

    now = datetime.now(UTC)
    applicable_items = 0
    conforming_items = 0
    for audit_item in audit.items:
        review_item = results_by_code[audit_item.checklist_code]
        if review_item.result == ChecklistResult.NONCONFORMING and review_item.priority is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Escolha a prioridade para {audit_item.checklist_label}.")
        audit_item.final_result = review_item.result
        audit_item.result = review_item.result
        if review_item.result != ChecklistResult.NOT_APPLICABLE:
            applicable_items += 1
        if review_item.result == ChecklistResult.CONFORMING:
            conforming_items += 1
        if review_item.result != ChecklistResult.NONCONFORMING:
            continue

        priority = review_item.priority
        assert priority is not None
        sla = target_for(priority)
        resolution_due_at = add_business_days(now, sla.correction_or_contestation_days)
        nonconformity = Nonconformity(
            code=next_nc_code(db),
            test_case_id=audit.test_case_id,
            audit_item_id=audit_item.id,
            assignee_email=audit.test_case.responsible_email or audit.test_case.author.email,
            description=f"{audit_item.checklist_label} não conforme no caso {audit.test_case.code}: {audit.test_case.title}.",
            severity=priority,
            due_date=resolution_due_at.date(),
            resolution_due_at=resolution_due_at,
            escalation_due_at=resolution_due_at,
            supervisor_email=supervisor_email,
        )
        db.add(nonconformity)
        db.flush()
        db.add(
            NonconformityHistory(
                nonconformity_id=nonconformity.id,
                actor_email=current_user.email,
                event_type="GENERATED",
                previous_status=None,
                new_status="OPEN",
                message=f"NC confirmada pelo revisor com prioridade {priority.value.lower()}.",
            )
        )
        notification = Notification(
            recipient_email=nonconformity.assignee_email or "",
            nonconformity_id=nonconformity.id,
            notification_type=NotificationType.NONCONFORMITY_ASSIGNED,
            title=f"{nonconformity.code} atribuída a você",
            message=f"A NC deve ser corrigida ou contestada até {nonconformity.resolution_due_at.date().isoformat()}.",
        )
        db.add(notification)
        send_notification_email(notification, notification.message)

    audit.status = AuditStatus.COMPLETED
    audit.completed_at = now
    audit.adherence_percentage = round((conforming_items / applicable_items) * 100) if applicable_items else 100
    db.commit()
    return serialize_audit(get_audit_or_404(audit.id, db), current_user)
