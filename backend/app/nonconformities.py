"""Acompanhamento de não conformidades, evidências e validação."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from .auth import get_current_user
from .database import get_db
from .email_service import send_notification_email
from .models import (
    Audit,
    AuditItem,
    Evidence,
    EvidenceStatus,
    EvidenceType,
    Nonconformity,
    NonconformityStatus,
    Notification,
    NotificationType,
    User,
    UserRole,
)
from .schemas import (
    EvidenceInput,
    EvidenceOutput,
    EvidenceReviewInput,
    NonconformityOutput,
)


router = APIRouter(prefix="/nonconformities", tags=["Não conformidades"])


def query_nonconformities():
    return select(Nonconformity).options(
        selectinload(Nonconformity.test_case),
        selectinload(Nonconformity.assignee),
        selectinload(Nonconformity.evidences).selectinload(Evidence.submitted_by),
        selectinload(Nonconformity.audit_item).selectinload(AuditItem.audit).selectinload(Audit.auditor),
    )


def get_nonconformity_or_404(nonconformity_id: str, db: Session) -> Nonconformity:
    nonconformity = db.scalar(query_nonconformities().where(Nonconformity.id == nonconformity_id))
    if nonconformity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Não conformidade não encontrada.")
    return nonconformity


def can_submit(nonconformity: Nonconformity, user: User) -> bool:
    return user.role == UserRole.ADMIN or nonconformity.assignee_id == user.id or nonconformity.assignee_email == user.email


def can_review(nonconformity: Nonconformity, user: User) -> bool:
    return user.role == UserRole.ADMIN or nonconformity.audit_item.audit.auditor_id == user.id


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
        can_submit_evidence=can_submit(nonconformity, user),
        can_review=can_review(nonconformity, user),
        evidences=[serialize_evidence(evidence) for evidence in nonconformity.evidences],
    )


@router.get("", response_model=list[NonconformityOutput])
def list_nonconformities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NonconformityOutput]:
    statement = query_nonconformities().order_by(Nonconformity.created_at.desc())
    if current_user.role == UserRole.RESPONSIBLE:
        statement = statement.where(
            or_(Nonconformity.assignee_id == current_user.id, Nonconformity.assignee_email == current_user.email)
        )
    nonconformities = db.scalars(statement).all()
    return [serialize_nonconformity(nonconformity, current_user) for nonconformity in nonconformities]


@router.post("/{nonconformity_id}/notify")
def retry_notification(
    nonconformity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    """Reenvia a notificação de uma NC sem repetir a auditoria."""
    nonconformity = get_nonconformity_or_404(nonconformity_id, db)
    if not (can_submit(nonconformity, current_user) or can_review(nonconformity, current_user)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não pode reenviar esta notificação.")
    notification = Notification(
        recipient_id=nonconformity.assignee_id,
        recipient_email=nonconformity.assignee_email or "",
        nonconformity_id=nonconformity.id,
        notification_type=NotificationType.NONCONFORMITY_ASSIGNED,
        title=f"Lembrete: {nonconformity.code} aguarda sua ação",
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
    nonconformity = get_nonconformity_or_404(nonconformity_id, db)
    if not can_submit(nonconformity, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Esta NC não está atribuída a você.")

    evidence = Evidence(
        nonconformity_id=nonconformity.id,
        submitted_by_id=current_user.id,
        description=payload.description,
        resource_url=payload.resource_url or None,
        evidence_type=payload.evidence_type,
    )
    db.add(evidence)
    nonconformity.status = (
        NonconformityStatus.CONTESTED
        if payload.evidence_type == EvidenceType.CONTESTATION
        else NonconformityStatus.WAITING_VALIDATION
    )
    auditor = nonconformity.audit_item.audit.auditor
    notification = Notification(
        recipient_id=auditor.id,
        recipient_email=auditor.email,
        nonconformity_id=nonconformity.id,
        notification_type=NotificationType.EVIDENCE_SUBMITTED,
        title=f"Evidência enviada para {nonconformity.code}",
        message=f"{current_user.full_name} enviou uma evidência para validação.",
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
    nonconformity = get_nonconformity_or_404(nonconformity_id, db)
    if not can_review(nonconformity, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Somente o auditor pode validar esta evidência.")
    evidence = next((item for item in nonconformity.evidences if item.id == payload.evidence_id), None)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidência não encontrada nesta NC.")
    if evidence.status != EvidenceStatus.SUBMITTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta evidência já foi revisada.")

    evidence.status = EvidenceStatus.APPROVED if payload.approved else EvidenceStatus.REJECTED
    evidence.reviewed_at = datetime.now(UTC)
    evidence.reviewer_comment = payload.comment or None
    if payload.approved:
        nonconformity.status = NonconformityStatus.RESOLVED
        nonconformity.resolved_at = datetime.now(UTC)
    else:
        nonconformity.status = NonconformityStatus.IN_CORRECTION
    notification = Notification(
        recipient_id=nonconformity.assignee_id,
        recipient_email=nonconformity.assignee_email or "",
        nonconformity_id=nonconformity.id,
        notification_type=NotificationType.EVIDENCE_REVIEWED,
        title=f"Evidência de {nonconformity.code} revisada",
        message="A evidência foi aprovada." if payload.approved else "A evidência precisa de ajustes.",
    )
    db.add(notification)
    send_notification_email(notification, notification.message)
    db.commit()
    db.expire_all()
    return serialize_nonconformity(get_nonconformity_or_404(nonconformity.id, db), current_user)
