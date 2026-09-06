"""Adiciona o responsável padrão para não conformidades do caso de teste.

Revision ID: 20260906_0003
Revises: 20260906_0002
Create Date: 2026-09-06
"""

from alembic import op
import sqlalchemy as sa


revision = "20260906_0003"
down_revision = "20260906_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("test_cases", sa.Column("responsible_email", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("test_cases", "responsible_email")
