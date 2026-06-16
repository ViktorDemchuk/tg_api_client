import logging
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApiKey, AuditLog, TelegramAccount, TelegramChat, User
from app.security import decode_access_token, hash_api_key

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate via JWT Bearer token or X-API-Key header."""

    # Try JWT Bearer first
    if credentials and credentials.credentials:
        try:
            payload = decode_access_token(credentials.credentials)
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
            user = db.get(User, int(user_id))
            if user is None or not user.is_active:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or disabled")
            return user
        except InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    # Try X-API-Key header
    api_key_header = request.headers.get("X-API-Key")
    if api_key_header:
        key_hash = hash_api_key(api_key_header)
        api_key = db.scalar(
            select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
        )
        if api_key is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        api_key.last_used_at = datetime.now(UTC)
        db.commit()
        user = db.get(User, api_key.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or disabled")
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication. Provide a Bearer token or X-API-Key header.",
    )


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def verify_account_ownership(
    db: Session,
    user: User,
    account_id: int,
) -> TelegramAccount:
    """Verify the user owns the given Telegram account. Returns the account if valid."""
    account = db.get(TelegramAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Telegram account not found")
    if account.user_id != user.id and user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Access denied to this Telegram account")
    return account


def verify_active_account(
    db: Session,
    user: User,
    account_id: int,
) -> TelegramAccount:
    """Verify ownership and ensure the account is active (not greylisted)."""
    account = verify_account_ownership(db, user, account_id)
    if not account.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account is in the greylist. Waiting for admin approval.",
        )
    return account


def audit_log(
    db: Session,
    user_id: int | None,
    action: str,
    *,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """Write an audit log entry."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    db.flush()


def resolve_account_by_tg_id(
    db: Session,
    user: User,
    tg_user_id: int,
) -> TelegramAccount:
    """Look up a Telegram account by its Telegram user ID, scoped to the current user."""
    account = db.scalar(
        select(TelegramAccount).where(
            TelegramAccount.telegram_user_id == tg_user_id,
            TelegramAccount.user_id == user.id,
        )
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Telegram account not found")
    if account.user_id != user.id and user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Access denied to this Telegram account")
    return account


def resolve_active_account_by_tg_id(
    db: Session,
    user: User,
    tg_user_id: int,
) -> TelegramAccount:
    """Look up by Telegram user ID and ensure the account is active."""
    account = resolve_account_by_tg_id(db, user, tg_user_id)
    if not account.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account is in the greylist. Waiting for admin approval.",
        )
    return account


def resolve_chat_by_tg_id(
    db: Session,
    account: TelegramAccount,
    tg_chat_id: int,
) -> TelegramChat:
    """Look up a Telegram chat by its Telegram chat ID within a specific account."""
    chat = db.scalar(
        select(TelegramChat).where(
            TelegramChat.telegram_chat_id == tg_chat_id,
            TelegramChat.telegram_account_id == account.id,
        )
    )
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat
