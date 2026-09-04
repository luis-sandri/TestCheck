"""Cria o schema inicial do TestCheck.

Revision ID: 20260904_0001
Revises:
Create Date: 2026-09-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260904_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("AUDITOR", "RESPONSIBLE", "ADMIN", native_enum=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "test_cases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("preconditions", sa.Text(), nullable=True),
        sa.Column("steps", sa.Text(), nullable=True),
        sa.Column("test_data", sa.Text(), nullable=True),
        sa.Column("expected_result", sa.Text(), nullable=True),
        sa.Column("approval_criteria", sa.Text(), nullable=True),
        sa.Column("author_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_test_cases_code", "test_cases", ["code"])

    op.create_table(
        "audits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("test_case_id", sa.String(length=36), nullable=False),
        sa.Column("auditor_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.Enum("DRAFT", "COMPLETED", native_enum=False), nullable=False),
        sa.Column("adherence_percentage", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["auditor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["test_case_id"], ["test_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audits_test_case_id", "audits", ["test_case_id"])

    op.create_table(
        "audit_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("audit_id", sa.String(length=36), nullable=False),
        sa.Column("checklist_code", sa.String(length=40), nullable=False),
        sa.Column("checklist_label", sa.String(length=220), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("result", sa.Enum("CONFORMING", "NONCONFORMING", "NOT_APPLICABLE", native_enum=False), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["audit_id"], ["audits.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("audit_id", "checklist_code", name="uq_audit_item_code"),
    )
    op.create_index("ix_audit_items_audit_id", "audit_items", ["audit_id"])

    op.create_table(
        "nonconformities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("test_case_id", sa.String(length=36), nullable=False),
        sa.Column("audit_item_id", sa.String(length=36), nullable=False),
        sa.Column("assignee_id", sa.String(length=36), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.Enum("LOW", "MEDIUM", "HIGH", native_enum=False), nullable=False),
        sa.Column("status", sa.Enum("OPEN", "IN_CORRECTION", "WAITING_VALIDATION", "RESOLVED", native_enum=False), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["audit_item_id"], ["audit_items.id"]),
        sa.ForeignKeyConstraint(["test_case_id"], ["test_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("audit_item_id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_nonconformities_assignee_id", "nonconformities", ["assignee_id"])
    op.create_index("ix_nonconformities_code", "nonconformities", ["code"])
    op.create_index("ix_nonconformities_test_case_id", "nonconformities", ["test_case_id"])

    op.create_table(
        "evidences",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("nonconformity_id", sa.String(length=36), nullable=False),
        sa.Column("submitted_by_id", sa.String(length=36), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("resource_url", sa.String(length=2048), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.Enum("SUBMITTED", "APPROVED", "REJECTED", native_enum=False), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_comment", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["nonconformity_id"], ["nonconformities.id"]),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidences_nonconformity_id", "evidences", ["nonconformity_id"])


def downgrade() -> None:
    op.drop_index("ix_evidences_nonconformity_id", table_name="evidences")
    op.drop_table("evidences")
    op.drop_index("ix_nonconformities_test_case_id", table_name="nonconformities")
    op.drop_index("ix_nonconformities_code", table_name="nonconformities")
    op.drop_index("ix_nonconformities_assignee_id", table_name="nonconformities")
    op.drop_table("nonconformities")
    op.drop_index("ix_audit_items_audit_id", table_name="audit_items")
    op.drop_table("audit_items")
    op.drop_index("ix_audits_test_case_id", table_name="audits")
    op.drop_table("audits")
    op.drop_index("ix_test_cases_code", table_name="test_cases")
    op.drop_table("test_cases")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
