"""Cria organizações e torna os dados operacionais multi-organização.

Revision ID: 20260914_0005
Revises: 20260910_0004
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260914_0005"
down_revision = "20260910_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_organization_member"),
    )
    op.add_column("users", sa.Column("active_organization_id", sa.String(length=36), nullable=True))
    op.add_column("scenarios", sa.Column("organization_id", sa.String(length=36), nullable=True))
    op.add_column("test_cases", sa.Column("organization_id", sa.String(length=36), nullable=True))
    op.create_index("ix_organization_memberships_organization_id", "organization_memberships", ["organization_id"])
    op.create_index("ix_organization_memberships_user_id", "organization_memberships", ["user_id"])
    op.create_index("ix_users_active_organization_id", "users", ["active_organization_id"])
    op.create_index("ix_scenarios_organization_id", "scenarios", ["organization_id"])
    op.create_index("ix_test_cases_organization_id", "test_cases", ["organization_id"])
    op.drop_index("ix_scenarios_zephyr_folder", table_name="scenarios")
    op.drop_index("ix_test_cases_code", table_name="test_cases")
    op.create_index("ix_scenarios_zephyr_folder", "scenarios", ["zephyr_folder"])
    op.create_index("ix_test_cases_code", "test_cases", ["code"])
    op.create_index(
        "uq_scenarios_organization_folder", "scenarios", ["organization_id", "zephyr_folder"], unique=True
    )
    op.create_index(
        "uq_test_case_code_by_scenario", "test_cases", ["organization_id", "scenario_id", "code"], unique=True
    )
    op.create_index(
        "uq_test_case_code_general", "test_cases", ["organization_id", "code"], unique=True,
        postgresql_where=sa.text("scenario_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_test_case_code_general", table_name="test_cases")
    op.drop_index("uq_test_case_code_by_scenario", table_name="test_cases")
    op.drop_index("uq_scenarios_organization_folder", table_name="scenarios")
    op.drop_index("ix_test_cases_organization_id", table_name="test_cases")
    op.drop_index("ix_scenarios_organization_id", table_name="scenarios")
    op.drop_index("ix_users_active_organization_id", table_name="users")
    op.drop_index("ix_organization_memberships_user_id", table_name="organization_memberships")
    op.drop_index("ix_organization_memberships_organization_id", table_name="organization_memberships")
    op.drop_column("test_cases", "organization_id")
    op.drop_column("scenarios", "organization_id")
    op.drop_column("users", "active_organization_id")
    op.drop_table("organization_memberships")
    op.drop_table("organizations")
