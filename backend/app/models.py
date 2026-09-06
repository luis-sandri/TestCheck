"""Entidades persistidas do TestCheck.

Esta camada contém somente o modelo de dados. As regras de cada fluxo serão
adicionadas aos endpoints nas próximas fases.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .database import Base


def uuid_key() -> str:
    return str(uuid4())


class UserRole(StrEnum):
    AUDITOR = "AUDITOR"
    RESPONSIBLE = "RESPONSIBLE"
    ADMIN = "ADMIN"


class AuditStatus(StrEnum):
    DRAFT = "DRAFT"
    COMPLETED = "COMPLETED"


class ChecklistResult(StrEnum):
    CONFORMING = "CONFORMING"
    NONCONFORMING = "NONCONFORMING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class NonconformitySeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class NonconformityStatus(StrEnum):
    OPEN = "OPEN"
    IN_CORRECTION = "IN_CORRECTION"
    WAITING_VALIDATION = "WAITING_VALIDATION"
    CONTESTED = "CONTESTED"
    RESOLVED = "RESOLVED"


class EvidenceStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class EvidenceType(StrEnum):
    CORRECTION = "CORRECTION"
    CONTESTATION = "CONTESTATION"


class NotificationType(StrEnum):
    NONCONFORMITY_ASSIGNED = "NONCONFORMITY_ASSIGNED"
    ACCOUNT_INVITATION = "ACCOUNT_INVITATION"
    EVIDENCE_SUBMITTED = "EVIDENCE_SUBMITTED"
    EVIDENCE_REVIEWED = "EVIDENCE_REVIEWED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_key)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False), default=UserRole.RESPONSIBLE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    authored_test_cases: Mapped[list[TestCase]] = relationship(
        back_populates="author", foreign_keys="TestCase.author_id"
    )
    audits: Mapped[list[Audit]] = relationship(back_populates="auditor")
    assigned_nonconformities: Mapped[list[Nonconformity]] = relationship(
        back_populates="assignee", foreign_keys="Nonconformity.assignee_id"
    )
    evidences: Mapped[list[Evidence]] = relationship(back_populates="submitted_by")
    notifications: Mapped[list[Notification]] = relationship(back_populates="recipient")


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_key)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str | None] = mapped_column(Text)
    preconditions: Mapped[str | None] = mapped_column(Text)
    steps: Mapped[str | None] = mapped_column(Text)
    test_data: Mapped[str | None] = mapped_column(Text)
    expected_result: Mapped[str | None] = mapped_column(Text)
    approval_criteria: Mapped[str | None] = mapped_column(Text)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    author: Mapped[User] = relationship(back_populates="authored_test_cases")
    audits: Mapped[list[Audit]] = relationship(back_populates="test_case", cascade="all, delete-orphan")
    nonconformities: Mapped[list[Nonconformity]] = relationship(back_populates="test_case")


class Audit(Base):
    __tablename__ = "audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_key)
    test_case_id: Mapped[str] = mapped_column(ForeignKey("test_cases.id"), nullable=False, index=True)
    auditor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[AuditStatus] = mapped_column(
        Enum(AuditStatus, native_enum=False), default=AuditStatus.DRAFT
    )
    adherence_percentage: Mapped[int | None] = mapped_column(Integer)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    test_case: Mapped[TestCase] = relationship(back_populates="audits")
    auditor: Mapped[User] = relationship(back_populates="audits")
    items: Mapped[list[AuditItem]] = relationship(
        back_populates="audit", cascade="all, delete-orphan", order_by="AuditItem.position"
    )


class AuditItem(Base):
    __tablename__ = "audit_items"
    __table_args__ = (UniqueConstraint("audit_id", "checklist_code", name="uq_audit_item_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_key)
    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id"), nullable=False, index=True)
    checklist_code: Mapped[str] = mapped_column(String(40))
    checklist_label: Mapped[str] = mapped_column(String(220))
    position: Mapped[int] = mapped_column(Integer)
    result: Mapped[ChecklistResult | None] = mapped_column(
        Enum(ChecklistResult, native_enum=False)
    )
    note: Mapped[str | None] = mapped_column(Text)

    audit: Mapped[Audit] = relationship(back_populates="items")
    nonconformity: Mapped[Nonconformity | None] = relationship(back_populates="audit_item")


class Nonconformity(Base):
    __tablename__ = "nonconformities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_key)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    test_case_id: Mapped[str] = mapped_column(ForeignKey("test_cases.id"), nullable=False, index=True)
    audit_item_id: Mapped[str] = mapped_column(ForeignKey("audit_items.id"), unique=True, nullable=False)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    assignee_email: Mapped[str | None] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[NonconformitySeverity] = mapped_column(
        Enum(NonconformitySeverity, native_enum=False), default=NonconformitySeverity.MEDIUM
    )
    status: Mapped[NonconformityStatus] = mapped_column(
        Enum(NonconformityStatus, native_enum=False), default=NonconformityStatus.OPEN
    )
    due_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    test_case: Mapped[TestCase] = relationship(back_populates="nonconformities")
    audit_item: Mapped[AuditItem] = relationship(back_populates="nonconformity")
    assignee: Mapped[User | None] = relationship(
        back_populates="assigned_nonconformities", foreign_keys=[assignee_id]
    )
    evidences: Mapped[list[Evidence]] = relationship(
        back_populates="nonconformity", cascade="all, delete-orphan"
    )


class Evidence(Base):
    __tablename__ = "evidences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_key)
    nonconformity_id: Mapped[str] = mapped_column(
        ForeignKey("nonconformities.id"), nullable=False, index=True
    )
    submitted_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    resource_url: Mapped[str | None] = mapped_column(String(2_048))
    file_name: Mapped[str | None] = mapped_column(String(255))
    evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType, native_enum=False), default=EvidenceType.CORRECTION
    )
    status: Mapped[EvidenceStatus] = mapped_column(
        Enum(EvidenceStatus, native_enum=False), default=EvidenceStatus.SUBMITTED
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer_comment: Mapped[str | None] = mapped_column(Text)

    nonconformity: Mapped[Nonconformity] = relationship(back_populates="evidences")
    submitted_by: Mapped[User] = relationship(back_populates="evidences")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_key)
    recipient_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    recipient_email: Mapped[str] = mapped_column(String(255), index=True)
    nonconformity_id: Mapped[str | None] = mapped_column(ForeignKey("nonconformities.id"), index=True)
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, native_enum=False)
    )
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    recipient: Mapped[User | None] = relationship(back_populates="notifications")
