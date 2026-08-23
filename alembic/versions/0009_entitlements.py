"""Product entitlements (per-org master switch) + launch_url on clients

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("oauth_clients", sa.Column("launch_url", sa.String(), nullable=True))

    op.create_table(
        "product_entitlements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("product_key", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "product_key", name="uq_org_product"),
    )


def downgrade() -> None:
    op.drop_table("product_entitlements")
    op.drop_column("oauth_clients", "launch_url")