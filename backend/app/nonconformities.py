"""Ciclo de vida, evidências, prazos e escalonamento das não conformidades."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from .auth import get_current_user
from .database import get_db
from .email_service import send_notification_email
from .config import get_settings
from .models import (
    Audit,
    AuditItem,
    Evidence,
    EvidenceStatus,
    EvidenceType,
    Nonconformity,
    NonconformityHistory,
    NonconformityStatus,
    Notification,
    NotificationType,
    Scenario,
    TestCase,
    User,
    UserRole,
)
from .schemas import (
    EvidenceInput,
    EvidenceOutput,
    EvidenceReviewInput,
    NonconformityHistoryOutput,
    NonconformityOutput,
    SupervisorDecisionInput,
)


router = APIRouter(prefix="/nonconformities", tags=["Não conformidades"])
settings = get_settings()

PRIORITY_SLA_DAYS = {"HIGH": (2, 1, 3), "MEDIUM": (5, 2, 7), "LOW": (10, 3, 14)}


def query_nonconformities():
    return select(Nonconformity).options(
        selectinload(Nonconformity.test_case).selectinload(TestCase.scenario),
        selectinload(Nonconformity.test_case).selectinload(TestCase.author),
        selectinload(Nonconformity.assignee),
        selectinload(Nonconformity.evidences).selectinload(Evidence.submitted_by),
        selectinload(Nonconformity.history),
        selectinload(Nonconformity.audit_item).selectinload(AuditItem.audit).selectinload(Audit.auditor),
    )


def record_history(
    db: Session,
    nonconformity: Nonconformity,
    actor_email: str | None,
    event_type: str,
    previous_status: NonconformityStatus | None,
    message: str,
) -> None:
    db.add(
        NonconformityHistory(
            nonconformity_id=nonconformity.id,
            actor_email=actor_email,
            event_type=event_type,
            previous_status=previous_status.value if previous_status else None,
            new_status=nonconformity.status.value,
            message=message,
        )
    )


def get_nonconformity_or_404(nonconformity_id: str, db: Session) -> Nonconformity:
    nonconformity = db.scalar(query_nonconformities().where(Nonconformity.id == nonconformity_id))
    if nonconformity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Não conformidade não encontrada.")
    return nonconformity


def scenario_for(nonconformity: Nonconformity) -> Scenario | None:
    return nonconformity.test_case.scenario


def can_submit(nonconformity: Nonconformity, user: User) -> bool:
    return (
        nonconformity.status not in {NonconformityStatus.RESOLVED, NonconformityStatus.ESCALATED}
        and (user.role == UserRole.ADMIN or nonconformity.assignee_id == user.id or nonconformity.assignee_email == user.email)
    )


def can_review(nonconformity: Nonconformity, user: User) -> bool:
    scenario = scenario_for(nonconformity)
    if scenario:
        return nonconformity.status != NonconformityStatus.ESCALATED and scenario.reviewer_email == user.email
    return nonconformity.status != NonconformityStatus.ESCALATED and (
        user.role == UserRole.ADMIN or nonconformity.audit_item.audit.auditor_id == user.id
    )


def can_decide_final(nonconformity: Nonconformity, user: User) -> bool:
    return nonconformity.status == NonconformityStatus.ESCALATED and nonconformity.supervisor_email == user.email


def serialize_evidence(evidence: Evidence) -> EvidenceOutput:
    return EvidenceOutput(
        id=evidence.id,
        description=evidence.description,
        resource_url=evidence.resource_url,
        evidence_type=evidence.evidence_type,
        status=evidence.status,
        submitted_by_name=evidence.submitted_by.full_name,
        submitted_at=evidence.submitted_at,
        reviewer_comment=evidence.reviewer_comment,
    )


def serialize_nonconformity(nonconformity: Nonconformity, user: User) -> NonconformityOutput:
    return NonconformityOutput(
        id=nonconformity.id,
        code=nonconformity.code,
        test_case_code=nonconformity.test_case.code,
        test_case_title=nonconformity.test_case.title,
        description=nonconformity.description,
        severity=nonconformity.severity,
        status=nonconformity.status,
        due_date=nonconformity.due_date.isoformat() if nonconformity.due_date else None,
        assignee_email=nonconformity.assignee_email,
        supervisor_email=nonconformity.supervisor_email,
        resolution_due_at=nonconformity.resolution_due_at,
        review_due_at=nonconformity.review_due_at,
        escalation_due_at=nonconformity.escalation_due_at,
        escalated_at=nonconformity.escalated_at,
        final_decision=nonconformity.final_decision,
        can_submit_evidence=can_submit(nonconformity, user),
        can_review=can_review(nonconformity, user),
        can_decide_final=can_decide_final(nonconformity, user),
        evidences=[serialize_evidence(evidence) for evidence in nonconformity.evidences],
        history=[
            NonconformityHistoryOutput(
                id=event.id,
                actor_email=event.actor_email,
                event_type=event.event_type,
                previous_status=event.previous_status,
                new_status=event.new_status,
                message=event.message,
                created_at=event.created_at,
            )
            for event in nonconformity.history
        ],
    )


def escalate_overdue_nonconformities(db: Session) -> None:
    """Aplica o escalonamento pendente quando a API é consultada.

    Em produção, este método também pode ser chamado por um cron diário sem
    mudar a regra de negócio ou duplicar notificações.
    """
    now = datetime.now(UTC)
    candidates = db.scalars(
        query_nonconformities().where(
            Nonconformity.status.notin_([NonconformityStatus.RESOLVED, NonconformityStatus.ESCALATED]),
            Nonconformity.escalation_due_at.is_not(None),
            Nonconformity.escalation_due_at <= now,
        )
    ).all()
    for nonconformity in candidates:
        previous_status = nonconformity.status
        nonconformity.status = NonconformityStatus.ESCALATED
        nonconformity.escalated_at = now
        record_history(
            db,
            nonconformity,
            None,
            "ESCALATED",
            previous_status,
            "Prazo de escalonamento vencido; decisão encaminhada ao supervisor.",
        )
        notification = Notification(
            recipient_email=nonconformity.supervisor_email or "",
            nonconformity_id=nonconformity.id,
            notification_type=NotificationType.EVIDENCE_REVIEWED,
            title=f"Decisão final necessária para {nonconformity.code}",
            message="O prazo da não conformidade venceu e a decisão final foi escalonada para você.",
        )
        db.add(notification)
        send_notification_email(notification, notification.message)
    if candidates:
        db.commit()


@router.get("", response_model=list[NonconformityOutput])
def list_nonconformities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NonconformityOutput]:
    escalate_overdue_nonconformities(db)
    statement = query_nonconformities().order_by(Nonconformity.created_at.desc())
    if current_user.role == UserRole.RESPONSIBLE:
        statement = statement.where(
            or_(
                Nonconformity.assignee_id == current_user.id,
                Nonconformity.assignee_email == current_user.email,
                Nonconformity.supervisor_email == current_user.email,
                Nonconformity.test_case.has(TestCase.scenario.has(Scenario.reviewer_email == current_user.email)),
            )
        )
    nonconformities = db.scalars(statement).all()
    return [serialize_nonconformity(nonconformity, current_user) for nonconformity in nonconformities]


@router.get("/escalate-overdue", tags=["Agendamento"])
def scheduled_escalation(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Endpoint chamado diariamente pelo Vercel Cron para aplicar escalonamentos."""
    expected = f"Bearer {settings.cron_secret}" if settings.cron_secret else None
    if expected is None or authorization is None or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Agendamento não autorizado.")
    escalate_overdue_nonconformities(db)
    return {"status": "ok", "message": "Prazos de escalonamento verificados."}


@router.post("/{nonconformity_id}/notify")
def retry_notification(
    nonconformity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    nonconformity = get_nonconformity_or_404(nonconformity_id, db)
    if not (can_submit(nonconformity, current_user) or can_review(nonconformity, current_user) or can_decide_final(nonconformity, current_user)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não pode reenviar esta notificação.")
    recipient = nonconformity.supervisor_email if nonconformity.status == NonconformityStatus.ESCALATED else nonconformity.assignee_email
    notification = Notification(
        recipient_email=recipient or "",
        nonconformity_id=nonconformity.id,
        notification_type=NotificationType.NONCONFORMITY_ASSIGNED,
        title=f"Lembrete: {nonconformity.code} aguarda uma ação",
        message=f"A não conformidade {nonconformity.code} continua disponível para acompanhamento no TestCheck.",
    )
    db.add(notification)
    email_sent = send_notification_email(notification, notification.message)
    db.commit()
    return {"email_sent": email_sent}


@router.post("/{nonconformity_id}/evidences", response_model=NonconformityOutput)
def submit_evidence(
    nonconformity_id: str,
    payload: EvidenceInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NonconformityOutput:
    escalate_overdue_nonconformities(db)
    nonconformity = get_nonconformity_or_404(nonconformity_id, db)
    if not can_submit(nonconformity, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Esta NC não está atribuída a você ou já foi escalada.")

    evidence = Evidence(
        nonconformity_id=nonconformity.id,
        submitted_by_id=current_user.id,
        description=payload.description,
        resource_url=payload.resource_url or None,
        evidence_type=payload.evidence_type,
    )
    db.add(evidence)
    previous_status = nonconformity.status
    nonconformity.status = NonconformityStatus.CONTESTED if payload.evidence_type == EvidenceType.CONTESTATION else NonconformityStatus.WAITING_VALIDATION
    _resolution_days, review_days, _escalation_days = PRIORITY_SLA_DAYS[nonconformity.severity.value]
    nonconformity.review_due_at = datetime.now(UTC) + timedelta(days=review_days)
    record_history(
        db,
        nonconformity,
        current_user.email,
        "CONTESTED" if payload.evidence_type == EvidenceType.CONTESTATION else "CORRECTION_SUBMITTED",
        previous_status,
        "Contestação enviada para análise." if payload.evidence_type == EvidenceType.CONTESTATION else "Evidência de correção enviada para validação.",
    )
    scenario = scenario_for(nonconformity)
    reviewer_email = scenario.reviewer_email if scenario else nonconformity.audit_item.audit.auditor.email
    notification = Notification(
        recipient_email=reviewer_email,
        nonconformity_id=nonconformity.id,
        notification_type=NotificationType.EVIDENCE_SUBMITTED,
        title=f"Evidência enviada para {nonconformity.code}",
        message=f"{current_user.full_name} enviou uma evidência; analise até {nonconformity.review_due_at.date().isoformat()}.",
    )
    db.add(notification)
    send_notification_email(notification, notification.message)
    db.commit()
    db.expire_all()
    return serialize_nonconformity(get_nonconformity_or_404(nonconformity.id, db), current_user)


@router.post("/{nonconformity_id}/review", response_model=NonconformityOutput)
def review_evidence(
    nonconformity_id: str,
    payload: EvidenceReviewInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NonconformityOutput:
    escalate_overdue_nonconformities(db)
    nonconformity = get_nonconformity_or_404(nonconformity_id, db)
    if not can_review(nonconformity, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Somente o revisor do cenário pode validar esta evidência.")
    evidence = next((item for item in nonconformity.evidences if item.id == payload.evidence_id), None)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidência não encontrada nesta NC.")
    if evidence.status != EvidenceStatus.SUBMITTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta evidência já foi revisada.")

    evidence.status = EvidenceStatus.APPROVED if payload.approved else EvidenceStatus.REJECTED
    evidence.reviewed_at = datetime.now(UTC)
    evidence.reviewer_comment = payload.comment or None
    previous_status = nonconformity.status
    if payload.approved:
        nonconformity.status = NonconformityStatus.RESOLVED
        nonconformity.resolved_at = datetime.now(UTC)
    else:
        nonconformity.status = NonconformityStatus.IN_CORRECTION
        resolution_days, _review_days, escalation_days = PRIORITY_SLA_DAYS[nonconformity.severity.value]
        now = datetime.now(UTC)
        nonconformity.resolution_due_at = now + timedelta(days=resolution_days)
        nonconformity.escalation_due_at = now + timedelta(days=escalation_days)
    record_history(
        db,
        nonconformity,
        current_user.email,
        "EVIDENCE_APPROVED" if payload.approved else "EVIDENCE_RETURNED",
        previous_status,
        "Evidência aprovada; NC resolvida." if payload.approved else "Evidência devolvida para correção complementar.",
    )
    notification = Notification(
        recipient_email=nonconformity.assignee_email or "",
        nonconformity_id=nonconformity.id,
        notification_type=NotificationType.EVIDENCE_REVIEWED,
        title=f"Evidência de {nonconformity.code} revisada",
        message="A evidência foi aprovada e a NC foi resolvida." if payload.approved else "A evidência precisa de ajustes antes da aprovação.",
    )
    db.add(notification)
    send_notification_email(notification, notification.message)
    db.commit()
    db.expire_all()
    return serialize_nonconformity(get_nonconformity_or_404(nonconformity.id, db), current_user)


@router.post("/{nonconformity_id}/supervisor-decision", response_model=NonconformityOutput)
def supervisor_decision(
    nonconformity_id: str,
    payload: SupervisorDecisionInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NonconformityOutput:
    escalate_overdue_nonconformities(db)
    nonconformity = get_nonconformity_or_404(nonconformity_id, db)
    if not can_decide_final(nonconformity, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Somente o supervisor do cenário pode registrar a decisão final.")
    previous_status = nonconformity.status
    nonconformity.final_decision = payload.comment
    if payload.approved:
        nonconformity.status = NonconformityStatus.RESOLVED
        nonconformity.resolved_at = datetime.now(UTC)
        message = "Supervisor aceitou a entrega ou contestação e encerrou a NC."
    else:
        nonconformity.status = NonconformityStatus.IN_CORRECTION
        resolution_days, _review_days, escalation_days = PRIORITY_SLA_DAYS[nonconformity.severity.value]
        now = datetime.now(UTC)
        nonconformity.resolution_due_at = now + timedelta(days=resolution_days)
        nonconformity.escalation_due_at = now + timedelta(days=escalation_days)
        message = "Supervisor manteve a NC e devolveu para correção final."
    record_history(db, nonconformity, current_user.email, "SUPERVISOR_DECISION", previous_status, message)
    db.add(
        Notification(
            recipient_email=nonconformity.assignee_email or "",
            nonconformity_id=nonconformity.id,
            notification_type=NotificationType.EVIDENCE_REVIEWED,
            title=f"Decisão final registrada para {nonconformity.code}",
            message=message,
        )
    )
    db.commit()
    db.expire_all()
    return serialize_nonconformity(get_nonconformity_or_404(nonconformity.id, db), current_user)
