"""Add category to permissions (for grouping the Roles UI)

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-23

"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfilled with a safe default; the seed script (re-run after this
    # migration) sets each existing permission's real category.
    op.add_column(
        "permissions", sa.Column("category", sa.String(), nullable=False, server_default="General")
    )


def downgrade() -> None:
    op.drop_column("permissions", "category")