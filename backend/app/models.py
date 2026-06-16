import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ═══════════════════════════════════════════════════════════
#  ENUMS
# ═══════════════════════════════════════════════════════════


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class TelegramAccountStatus(str, enum.Enum):
    pending = "pending"
    code_sent = "code_sent"
    authorized = "authorized"
    disconnected = "disconnected"
    error = "error"


class TelegramCommandStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


# ═══════════════════════════════════════════════════════════
#  USERS
# ═══════════════════════════════════════════════════════════


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.user, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    telegram_accounts: Mapped[list["TelegramAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[list["ApiKey"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")


# ═══════════════════════════════════════════════════════════
#  TELEGRAM ACCOUNTS
# ═══════════════════════════════════════════════════════════


class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "phone", name="uq_telegram_accounts_user_phone"),
        UniqueConstraint("user_id", "telegram_user_id", name="uq_telegram_accounts_user_tgid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger)
    display_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[TelegramAccountStatus] = mapped_column(
        Enum(TelegramAccountStatus), default=TelegramAccountStatus.pending, nullable=False
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="telegram_accounts")
    session: Mapped["TelegramSession | None"] = relationship(
        back_populates="account", cascade="all, delete-orphan", uselist=False
    )
    chats: Mapped[list["TelegramChat"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


# ═══════════════════════════════════════════════════════════
#  TELEGRAM SESSIONS (encrypted)
# ═══════════════════════════════════════════════════════════


class TelegramSession(Base):
    __tablename__ = "telegram_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_account_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_accounts.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    encrypted_session: Mapped[str | None] = mapped_column(Text)
    phone_code_hash: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    account: Mapped[TelegramAccount] = relationship(back_populates="session")


# ═══════════════════════════════════════════════════════════
#  TELEGRAM CHATS (cached metadata)
# ═══════════════════════════════════════════════════════════


class TelegramChat(Base):
    __tablename__ = "telegram_chats"
    __table_args__ = (
        UniqueConstraint(
            "telegram_account_id", "telegram_chat_id",
            name="uq_telegram_chats_account_chat",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_account_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str | None] = mapped_column(String(512))
    chat_type: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    unread_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_message_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_subscribed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    account: Mapped[TelegramAccount] = relationship(back_populates="chats")
    messages: Mapped[list["TelegramMessage"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )


# ═══════════════════════════════════════════════════════════
#  TELEGRAM MESSAGES (cached)
# ═══════════════════════════════════════════════════════════


class TelegramMessage(Base):
    __tablename__ = "telegram_messages"
    __table_args__ = (
        UniqueConstraint(
            "chat_id", "telegram_message_id",
            name="uq_telegram_messages_chat_msg",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_chats.id", ondelete="CASCADE"), nullable=False, index=True
    )
    telegram_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sender_name: Mapped[str | None] = mapped_column(String(255))
    sender_id: Mapped[int | None] = mapped_column(BigInteger)
    message_text: Mapped[str | None] = mapped_column(Text)
    message_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    views: Mapped[int | None] = mapped_column(Integer)
    forwards: Mapped[int | None] = mapped_column(Integer)
    reactions: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    chat: Mapped[TelegramChat] = relationship(back_populates="messages")


# ═══════════════════════════════════════════════════════════
#  TELEGRAM COMMANDS (queue between API and worker)
# ═══════════════════════════════════════════════════════════


class TelegramCommand(Base):
    __tablename__ = "telegram_commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_account_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    command: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[TelegramCommandStatus] = mapped_column(
        Enum(TelegramCommandStatus), default=TelegramCommandStatus.pending, nullable=False, index=True
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ═══════════════════════════════════════════════════════════
#  API KEYS
# ═══════════════════════════════════════════════════════════


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="api_keys")


# ═══════════════════════════════════════════════════════════
#  AUDIT LOGS
# ═══════════════════════════════════════════════════════════


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[str | None] = mapped_column(String(128))
    details: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User | None] = relationship(back_populates="audit_logs")
