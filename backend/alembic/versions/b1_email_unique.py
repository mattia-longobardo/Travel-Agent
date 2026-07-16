"""email unique

Revision ID: b1_email_unique
Revises: 40b12c6b4752
Create Date: 2026-06-19 12:00:00
"""
from alembic import op

revision = "b1_email_unique"
down_revision = "40b12c6b4752"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
