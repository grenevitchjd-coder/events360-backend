# events360-backend: alembic/versions/0012_oauth_code_user_cascade.py
"""OAuth authorization codes die with their user.

Deleting a staff member 500'd in production (FK violation) if they had
ever launched EventNXT: /oauth/authorize leaves rows in
oauth_authorization_codes, and its user_id FK had no ondelete. The codes
are 10-minute single-use ephemera — there is nothing to preserve, so
CASCADE is unambiguous. Same recreate-the-FK pattern as 0003.

Revision ID: 0012
Revises: 0011
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

FK = ("oauth_authorization_codes_user_id_fkey", "oauth_authorization_codes", "user_id", "users", "id")


def upgrade() -> None:
    name, table, col, ref_table, ref_col = FK
    op.drop_constraint(name, table, type_="foreignkey")
    op.create_foreign_key(name, table, ref_table, [col], [ref_col], ondelete="CASCADE")


def downgrade() -> None:
    name, table, col, ref_table, ref_col = FK
    op.drop_constraint(name, table, type_="foreignkey")
    op.create_foreign_key(name, table, ref_table, [col], [ref_col])