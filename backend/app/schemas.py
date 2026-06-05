from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════════


class UserRegister(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    username: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=6, max_length=256)


class UserLogin(BaseModel):
    email: str
    password: str


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=128)
    password: str | None = Field(default=None, min_length=6, max_length=256)
    email: str | None = Field(default=None, min_length=5, max_length=255)



# ═══════════════════════════════════════════════════════════
#  TELEGRAM ACCOUNTS
# ═══════════════════════════════════════════════════════════


class TelegramAccountCreate(BaseModel):
    phone: str = Field(min_length=5, max_length=32)


class TelegramAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    phone: str
    telegram_user_id: int | None = None
    display_name: str | None = None
    status: str
    last_error: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TelegramSubmitCodeRequest(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    password: str | None = Field(default=None, min_length=1, max_length=256)


class TelegramSubmitPasswordRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class TelegramAuthResult(BaseModel):
    status: str
    authorized: bool = False
    needs_password: bool = False
    phone: str | None = None
    account_id: int | None = None
    qr_link: str | None = None


class TelegramSessionExport(BaseModel):
    phone: str
    session_string: str | None = None



# ═══════════════════════════════════════════════════════════
#  TELEGRAM CHATS
# ═══════════════════════════════════════════════════════════


class TelegramChatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_account_id: int
    telegram_chat_id: int
    title: str | None = None
    chat_type: str = "unknown"
    username: str | None = None
    unread_count: int = 0
    last_message_date: datetime | None = None
    is_subscribed: bool = True
    synced_at: datetime | None = None


# ═══════════════════════════════════════════════════════════
#  TELEGRAM MESSAGES
# ═══════════════════════════════════════════════════════════


class TelegramMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int
    telegram_message_id: int
    sender_name: str | None = None
    sender_id: int | None = None
    message_text: str | None = None
    message_date: datetime
    views: int | None = None
    forwards: int | None = None
    reactions: dict | None = None
    raw_payload: dict | None = None
    created_at: datetime


class SendMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)


class SendMessageResult(BaseModel):
    status: str
    telegram_message_id: int | None = None


class JoinChannelRequest(BaseModel):
    channel_url: str = Field(min_length=1, max_length=512)


# ═══════════════════════════════════════════════════════════
#  API KEYS
# ═══════════════════════════════════════════════════════════


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class ApiKeyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    key_prefix: str
    name: str
    is_active: bool
    last_used_at: datetime | None = None
    created_at: datetime


class ApiKeyCreatedRead(ApiKeyRead):
    """Returned only once at creation time — includes the full key."""
    api_key: str


# ═══════════════════════════════════════════════════════════
#  AUDIT LOGS
# ═══════════════════════════════════════════════════════════


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    action: str
    target_type: str | None = None
    target_id: str | None = None
    details: dict | None = None
    ip_address: str | None = None
    created_at: datetime


# ═══════════════════════════════════════════════════════════
#  ADMIN
# ═══════════════════════════════════════════════════════════


class AdminUserRead(UserRead):
    telegram_accounts: list[TelegramAccountRead] = Field(default_factory=list)


class AdminStatsRead(BaseModel):
    total_users: int = 0
    active_users: int = 0
    total_telegram_accounts: int = 0
    authorized_accounts: int = 0
    total_chats: int = 0
    total_messages: int = 0


class AdminDisableRequest(BaseModel):
    is_active: bool


# ═══════════════════════════════════════════════════════════
#  SEARCH
# ═══════════════════════════════════════════════════════════


class MessageSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    account_id: int | None = None
    limit: int = Field(default=50, ge=1, le=200)
