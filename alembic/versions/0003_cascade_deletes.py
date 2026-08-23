"""Add ON DELETE CASCADE for org/event/role/staff deletion

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-23

"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

# (constraint_name, table, column, references_table, references_column)
CASCADE_FKS = [
    ("users_organization_id_fkey", "users", "organization_id", "organizations", "id"),
    ("events_organization_id_fkey", "events", "organization_id", "organizations", "id"),
    ("roles_organization_id_fkey", "roles", "organization_id", "organizations", "id"),
    ("staff_assignments_user_id_fkey", "staff_assignments", "user_id", "users", "id"),
    ("staff_assignments_role_id_fkey", "staff_assignments", "role_id", "roles", "id"),
    ("staff_assignments_event_id_fkey", "staff_assignments", "event_id", "events", "id"),
    ("role_permissions_role_id_fkey", "role_permissions", "role_id", "roles", "id"),
    ("role_permissions_permission_id_fkey", "role_permissions", "permission_id", "permissions", "id"),
]


def upgrade() -> None:
    for constraint_name, table, column, ref_table, ref_column in CASCADE_FKS:
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(
            constraint_name, table, ref_table, [column], [ref_column], ondelete="CASCADE"
        )


def downgrade() -> None:
    for constraint_name, table, column, ref_table, ref_column in CASCADE_FKS:
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(constraint_name, table, ref_table, [column], [ref_column])