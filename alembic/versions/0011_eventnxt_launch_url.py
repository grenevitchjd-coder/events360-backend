# events360-backend/alembic/versions/0011_eventnxt_launch_url.py
"""Data fix: point EventNXT's launch_url at the new custom domain

The Launch button on the org Apps tab renders oauth_clients.launch_url.
The redirect_uris allowlist already contains the new
eventnxt-api.events360.app callback, but launch_url was still the old
herokuapp host — so launching from Events360 landed on the old page.
Pure data migration, no schema change; safe to re-run (idempotent).

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-06

"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

NEW_LAUNCH_URL = "https://eventnxt-api.events360.app/auth/login"


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE oauth_clients SET launch_url = :url WHERE client_id = 'eventnxt'"
        ).bindparams(url=NEW_LAUNCH_URL)
    )


def downgrade() -> None:
    # Deliberate no-op: the old value was a generated herokuapp hostname —
    # restoring it automatically would just re-break the Launch button.
    # If a rollback is ever truly needed, set launch_url by hand.
    pass