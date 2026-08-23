"""Add status (active/locked) to events

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    event_status = postgresql.ENUM("active", "locked", name="event_status")
    # Explicit creation needed here: op.add_column has no associated table-creation
    # event to auto-create the enum type (unlike op.create_table), so it must be
    # created up front, once, with checkfirst to stay idempotent.
    event_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "events",
        sa.Column("status", event_status, nullable=False, server_default="active"),
    )


def downgrade() -> None:
    op.drop_column("events", "status")
    postgresql.ENUM(name="event_status").drop(op.get_bind(), checkfirst=True)