"""run telemetry: per-turn token/latency/path metrics

Revision ID: b3_run_telemetry
Revises: b2_chat_org
Create Date: 2026-06-21 12:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "b3_run_telemetry"
down_revision = "b2_chat_org"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "run_telemetry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("node_path", sa.JSON(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completion_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("model", sa.String(length=80), nullable=True),
        sa.Column("ok", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_run_telemetry_chat_id", "run_telemetry", ["chat_id"])
    op.create_index("ix_run_telemetry_user_id", "run_telemetry", ["user_id"])
    op.create_index("ix_run_telemetry_created_at", "run_telemetry", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_run_telemetry_created_at", table_name="run_telemetry")
    op.drop_index("ix_run_telemetry_user_id", table_name="run_telemetry")
    op.drop_index("ix_run_telemetry_chat_id", table_name="run_telemetry")
    op.drop_table("run_telemetry")
