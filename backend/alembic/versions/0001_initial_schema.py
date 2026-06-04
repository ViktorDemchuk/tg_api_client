"""Initial schema — 7 tables for multi-user Telegram client.

Revision ID: 0001
Revises: (none)
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ──
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("username", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(512), nullable=False),
        sa.Column("role", sa.Enum("admin", "user", name="userrole"), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── telegram_accounts ──
    op.create_table(
        "telegram_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger()),
        sa.Column("display_name", sa.String(255)),
        sa.Column("status", sa.Enum("pending", "code_sent", "authorized", "disconnected", "error", name="telegramaccountstatus"), nullable=False, server_default="pending"),
        sa.Column("last_error", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "phone", name="uq_telegram_accounts_user_phone"),
    )

    # ── telegram_sessions ──
    op.create_table(
        "telegram_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_account_id", sa.Integer(), sa.ForeignKey("telegram_accounts.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("encrypted_session", sa.Text()),
        sa.Column("phone_code_hash", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── telegram_chats ──
    op.create_table(
        "telegram_chats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_account_id", sa.Integer(), sa.ForeignKey("telegram_accounts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(512)),
        sa.Column("chat_type", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("username", sa.String(255)),
        sa.Column("unread_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_message_date", sa.DateTime(timezone=True)),
        sa.Column("is_subscribed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata_json", postgresql.JSONB()),
        sa.Column("synced_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("telegram_account_id", "telegram_chat_id", name="uq_telegram_chats_account_chat"),
    )

    # ── telegram_messages ──
    op.create_table(
        "telegram_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chat_id", sa.Integer(), sa.ForeignKey("telegram_chats.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=False),
        sa.Column("sender_name", sa.String(255)),
        sa.Column("sender_id", sa.BigInteger()),
        sa.Column("message_text", sa.Text()),
        sa.Column("message_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("views", sa.Integer()),
        sa.Column("forwards", sa.Integer()),
        sa.Column("reactions", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("chat_id", "telegram_message_id", name="uq_telegram_messages_chat_msg"),
    )

    # ── telegram_commands ──
    op.create_table(
        "telegram_commands",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_account_id", sa.Integer(), sa.ForeignKey("telegram_accounts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("command", sa.String(64), nullable=False, index=True),
        sa.Column("status", sa.Enum("pending", "running", "succeeded", "failed", name="telegramcommandstatus"), nullable=False, server_default="pending", index=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── api_keys ──
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("key_hash", sa.String(512), nullable=False),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── audit_logs ──
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), index=True),
        sa.Column("action", sa.String(128), nullable=False, index=True),
        sa.Column("target_type", sa.String(64)),
        sa.Column("target_id", sa.String(128)),
        sa.Column("details", postgresql.JSONB()),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("api_keys")
    op.drop_table("telegram_commands")
    op.drop_table("telegram_messages")
    op.drop_table("telegram_chats")
    op.drop_table("telegram_sessions")
    op.drop_table("telegram_accounts")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS telegramaccountstatus")
    op.execute("DROP TYPE IF EXISTS telegramcommandstatus")
