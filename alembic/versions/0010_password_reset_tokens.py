# events360-backend/alembic/versions/0010_password_reset_tokens.py
"""Password reset tokens (admin-issued only, no self-service flow)

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # Exactly one of the two account FKs is set (enforced by the check
        # constraint below) — one table serves both org Users and
        # PlatformAdmins so the public redeem endpoint is a single flow.
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "platform_admin_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("platform_admins.id", ondelete="CASCADE"),
            nullable=True,
        ),
        # SHA-256 of the raw token. The raw token only ever exists inside the
        # emailed link — a database leak can't mint working reset links.
        sa.Column("token_hash", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        # Audit trail: which org admin or platform admin issued the link.
        # SET NULL (not CASCADE) so deleting the issuer never deletes the
        # evidence that a link was issued.
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by_admin_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("platform_admins.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "(user_id IS NULL) != (platform_admin_id IS NULL)",
            name="ck_reset_token_exactly_one_account",
        ),
    )


def downgrade() -> None:
    op.drop_table("password_reset_tokens")