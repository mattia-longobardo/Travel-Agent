"""chat org: status, trashed_at, groups

Revision ID: b2_chat_org
Revises: b1_email_unique
Create Date: 2026-06-19 12:10:00
"""
from alembic import op
import sqlalchemy as sa

revision = "b2_chat_org"
down_revision = "b1_email_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_groups_owner_id", "chat_groups", ["owner_id"])
    op.add_column("chats", sa.Column("status", sa.String(length=10), server_default="active", nullable=False))
    op.add_column("chats", sa.Column("trashed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("chats", sa.Column("chat_group_id", sa.Integer(), nullable=True))
    op.create_index("ix_chats_status", "chats", ["status"])
    op.create_index("ix_chats_chat_group_id", "chats", ["chat_group_id"])
    op.create_foreign_key("fk_chats_chat_group", "chats", "chat_groups", ["chat_group_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_chats_chat_group", "chats", type_="foreignkey")
    op.drop_index("ix_chats_chat_group_id", table_name="chats")
    op.drop_index("ix_chats_status", table_name="chats")
    op.drop_column("chats", "chat_group_id")
    op.drop_column("chats", "trashed_at")
    op.drop_column("chats", "status")
    op.drop_index("ix_chat_groups_owner_id", table_name="chat_groups")
    op.drop_table("chat_groups")
