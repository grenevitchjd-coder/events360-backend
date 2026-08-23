"""Add retention_days and retention_reminder_sent_at to events

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-23

"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("events", sa.Column("retention_days", sa.Integer(), nullable=False, server_default="30"))
    op.add_column(
        "events", sa.Column("retention_reminder_sent_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("events", "retention_reminder_sent_at")
    op.drop_column("events", "retention_days")