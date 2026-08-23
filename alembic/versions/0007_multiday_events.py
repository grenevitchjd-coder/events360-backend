"""Support multi-day events: event_date -> start_date, add end_date

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-23

"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("events", "event_date", new_column_name="start_date")
    op.add_column("events", sa.Column("end_date", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("events", "end_date")
    op.alter_column("events", "start_date", new_column_name="event_date")