"""Adiciona cenários do Zephyr e a trilha de ciclo de vida das NCs.

Revision ID: 20260910_0004
Revises: 20260906_0003
Create Date: 2026-09-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260910_0004"
down_revision = "20260906_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("zephyr_folder", sa.String(length=500), nullable=False, unique=True),
        sa.Column("reviewer_email", sa.String(length=255), nullable=False),
        sa.Column("supervisor_email", sa.String(length=255), nullable=False),
        sa.Column("created_by_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column("test_cases", sa.Column("scenario_id", sa.String(length=36), nullable=True))
    op.create_foreign_key("fk_test_cases_scenario", "test_cases", "scenarios", ["scenario_id"], ["id"])
    op.add_column("audit_items", sa.Column("suggested_result", sa.String(length=32), nullable=True))
    op.add_column("audit_items", sa.Column("final_result", sa.String(length=32), nullable=True))
    op.add_column("nonconformities", sa.Column("resolution_due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("nonconformities", sa.Column("review_due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("nonconformities", sa.Column("escalation_due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("nonconformities", sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("nonconformities", sa.Column("supervisor_email", sa.String(length=255), nullable=True))
    op.add_column("nonconformities", sa.Column("final_decision", sa.Text(), nullable=True))
    op.create_table(
        "nonconformity_history",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("nonconformity_id", sa.String(length=36), sa.ForeignKey("nonconformities.id"), nullable=False),
        sa.Column("actor_email", sa.String(length=255), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("previous_status", sa.String(length=40), nullable=True),
        sa.Column("new_status", sa.String(length=40), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("nonconformity_history")
    for column in ("final_decision", "supervisor_email", "escalated_at", "escalation_due_at", "review_due_at", "resolution_due_at"):
        op.drop_column("nonconformities", column)
    op.drop_column("audit_items", "final_result")
    op.drop_column("audit_items", "suggested_result")
    op.drop_constraint("fk_test_cases_scenario", "test_cases", type_="foreignkey")
    op.drop_column("test_cases", "scenario_id")
    op.drop_table("scenarios")
