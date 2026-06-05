"""Manages Telethon client lifecycle for multiple Telegram accounts."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
)
from telethon.sessions import StringSession
from telethon.tl.types import Channel as TgChannel, Chat as TgChat, User as TgUser

from app.config import settings
from app.models import (
    TelegramAccount,
    TelegramAccountStatus,
    TelegramChat,
    TelegramMessage,
    TelegramSession,
)
from app.security import decrypt_session, encrypt_session

logger = logging.getLogger(__name__)


def make_client(session_string: str | None = None) -> TelegramClient:
    """Create a TelegramClient using the app-level API credentials."""
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        raise RuntimeError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be configured")
    return TelegramClient(
        StringSession(session_string or ""),
        settings.telegram_api_id,
        settings.telegram_api_hash,
        device_model=settings.telegram_device_model,
        system_version=settings.telegram_system_version,
        app_version=settings.telegram_app_version,
    )


def load_session_string(db: Session, account: TelegramAccount) -> str | None:
    """Load and decrypt the session string for an account."""
    session = db.query(TelegramSession).filter(
        TelegramSession.telegram_account_id == account.id
    ).first()
    if session and session.encrypted_session:
        try:
            return decrypt_session(session.encrypted_session)
        except Exception as exc:
            logger.error("Failed to decrypt session for account %s: %s", account.id, exc)
    return None


def save_session_string(db: Session, account: TelegramAccount, session_string: str) -> None:
    """Encrypt and save the session string."""
    encrypted = encrypt_session(session_string)
    session = db.query(TelegramSession).filter(
        TelegramSession.telegram_account_id == account.id
    ).first()
    if session:
        session.encrypted_session = encrypted
        session.updated_at = datetime.now(UTC)
    else:
        session = TelegramSession(
            telegram_account_id=account.id,
            encrypted_session=encrypted,
        )
        db.add(session)
    db.flush()


async def handle_send_code(
    client: TelegramClient,
    db: Session,
    account: TelegramAccount,
    phone: str,
) -> dict:
    """Send a Telegram login code."""
    if await client.is_user_authorized():
        session_string = client.session.save()
        save_session_string(db, account, session_string)
        account.status = TelegramAccountStatus.authorized
        account.last_error = None
        # Get user info
        me = await client.get_me()
        if me:
            account.telegram_user_id = me.id
            account.display_name = _display_name(me)
        db.commit()
        return {"status": "already_authorized", "authorized": True, "phone": phone}

    sent = await client.send_code_request(phone)
    logger.info("send_code_request result: %s", sent)
    sent_type = type(sent.type).__name__
    logger.info("Code sent via: %s", sent_type)
    # Store phone_code_hash
    session = db.query(TelegramSession).filter(
        TelegramSession.telegram_account_id == account.id
    ).first()
    if session:
        session.phone_code_hash = sent.phone_code_hash
    account.status = TelegramAccountStatus.code_sent
    account.last_error = None
    db.commit()
    return {"status": "code_sent", "authorized": False, "phone": phone, "sent_type": sent_type}


async def handle_submit_code(
    client: TelegramClient,
    db: Session,
    account: TelegramAccount,
    phone: str,
    code: str,
    password: str | None = None,
) -> dict:
    """Submit the Telegram login code and optional 2FA password."""
    session = db.query(TelegramSession).filter(
        TelegramSession.telegram_account_id == account.id
    ).first()
    phone_code_hash = session.phone_code_hash if session else None
    if not phone_code_hash:
        raise RuntimeError("Send code first")

    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
    except SessionPasswordNeededError:
        if not password:
            return {"status": "password_required", "authorized": False, "needs_password": True}
        await client.sign_in(password=password)

    authorized = await client.is_user_authorized()
    if authorized:
        session_string = client.session.save()
        save_session_string(db, account, session_string)
        account.status = TelegramAccountStatus.authorized
        account.last_error = None
        if session:
            session.phone_code_hash = None
        me = await client.get_me()
        if me:
            account.telegram_user_id = me.id
            account.display_name = _display_name(me)
        db.commit()
    return {"status": "authorized" if authorized else "not_authorized", "authorized": authorized}


async def handle_request_qr(
    worker,
    db: Session,
    account: TelegramAccount,
) -> dict:
    """Request a Telegram login QR code."""
    import asyncio
    if not worker.client.is_connected():
        await worker.client.connect()

    if await worker.client.is_user_authorized():
        session_string = worker.client.session.save()
        save_session_string(db, account, session_string)
        account.status = TelegramAccountStatus.authorized
        account.last_error = None
        me = await worker.client.get_me()
        if me:
            account.telegram_user_id = me.id
            account.display_name = _display_name(me)
        db.commit()
        return {"status": "already_authorized", "authorized": True, "phone": me.phone if me else None, "account_id": account.id}

    worker.qr_login = await worker.client.qr_login()
    logger.info("QR login URL generated: %s", worker.qr_login.url)
    
    return {"status": "qr_generated", "authorized": False, "qr_link": worker.qr_login.url}


async def _complete_qr_auth(worker, db: Session, account: TelegramAccount) -> dict:
    from sqlalchemy import select
    me = await worker.client.get_me()
    phone = me.phone if me.phone else f"+{me.id}"
    
    existing = db.scalar(
        select(TelegramAccount).where(
            TelegramAccount.user_id == account.user_id,
            TelegramAccount.phone == phone,
            TelegramAccount.id != account.id
        )
    )
    
    session_string = worker.client.session.save()
    
    if existing:
        save_session_string(db, existing, session_string)
        existing.status = TelegramAccountStatus.authorized
        existing.telegram_user_id = me.id
        existing.display_name = _display_name(me)
        existing.last_error = None
        
        db.delete(account)
        db.commit()
        
        return {
            "status": "authorized",
            "authorized": True,
            "phone": phone,
            "account_id": existing.id
        }
    else:
        account.phone = phone
        save_session_string(db, account, session_string)
        account.status = TelegramAccountStatus.authorized
        account.telegram_user_id = me.id
        account.display_name = _display_name(me)
        account.last_error = None
        db.commit()
        
        return {
            "status": "authorized",
            "authorized": True,
            "phone": phone,
            "account_id": account.id
        }


async def handle_wait_qr(
    worker,
    db: Session,
    account: TelegramAccount,
) -> dict:
    """Wait for the QR code to be scanned."""
    import asyncio
    
    if not getattr(worker, "qr_login", None):
        raise RuntimeError("QR login session not started. Please request QR first.")

    # Check if already authorized (from previous tick or background scan)
    if await worker.client.is_user_authorized():
        return await _complete_qr_auth(worker, db, account)

    try:
        await worker.qr_login.wait(timeout=8)
    except SessionPasswordNeededError:
        return {"status": "password_required", "authorized": False, "needs_password": True}
    except asyncio.TimeoutError:
        # Check again in case it authorized right at the timeout boundary
        if await worker.client.is_user_authorized():
            return await _complete_qr_auth(worker, db, account)
        return {"status": "pending", "authorized": False}

    # If wait completed, check if we're now authorized
    if await worker.client.is_user_authorized():
        return await _complete_qr_auth(worker, db, account)
        
    return {"status": "not_authorized", "authorized": False}


async def handle_submit_password(
    worker,
    db: Session,
    account: TelegramAccount,
    password: str,
) -> dict:
    """Submit 2FA password to complete sign-in."""
    await worker.client.sign_in(password=password)
    
    authorized = await worker.client.is_user_authorized()
    if authorized:
        return await _complete_qr_auth(worker, db, account)
            
    return {"status": "not_authorized", "authorized": False}


async def sync_chats(
    client: TelegramClient,
    db: Session,
    account: TelegramAccount,
) -> None:
    """Fetch all dialogs and upsert into telegram_chats."""
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        chat_type = _chat_type(entity)
        telegram_chat_id = dialog.id

        values = {
            "telegram_account_id": account.id,
            "telegram_chat_id": telegram_chat_id,
            "title": dialog.title or dialog.name,
            "chat_type": chat_type,
            "username": getattr(entity, "username", None),
            "unread_count": dialog.unread_count or 0,
            "last_message_date": dialog.date,
            "is_subscribed": not getattr(entity, "left", False),
            "metadata_json": {
                "participants_count": getattr(entity, "participants_count", None),
            },
            "synced_at": datetime.now(UTC),
        }

        stmt = insert(TelegramChat).values(**values).on_conflict_do_update(
            constraint="uq_telegram_chats_account_chat",
            set_={
                "title": values["title"],
                "chat_type": values["chat_type"],
                "username": values["username"],
                "unread_count": values["unread_count"],
                "last_message_date": values["last_message_date"],
                "is_subscribed": values["is_subscribed"],
                "metadata_json": values["metadata_json"],
                "synced_at": values["synced_at"],
            },
        )
        db.execute(stmt)
    db.commit()


async def sync_messages(
    client: TelegramClient,
    db: Session,
    account: TelegramAccount,
    limit_per_chat: int | None = None,
) -> None:
    """Fetch recent messages for all chats."""
    limit = limit_per_chat or settings.messages_per_chat
    chats = db.query(TelegramChat).filter(
        TelegramChat.telegram_account_id == account.id,
    ).all()

    for chat in chats:
        try:
            entity = await client.get_entity(chat.telegram_chat_id)
            async for msg in client.iter_messages(entity, limit=limit):
                _store_message(db, chat, msg)
            db.commit()
        except Exception as exc:
            logger.warning("Failed to sync messages for chat %s: %s", chat.telegram_chat_id, exc)
            db.rollback()


async def send_message(
    client: TelegramClient,
    telegram_chat_id: int,
    text: str,
) -> dict:
    """Send a message to a Telegram chat."""
    entity = await client.get_entity(telegram_chat_id)
    msg = await client.send_message(entity, text)
    return {"status": "sent", "telegram_message_id": msg.id}


async def join_channel(
    client: TelegramClient,
    db: Session,
    account: TelegramAccount,
    channel_url: str,
) -> dict:
    """Join a channel/group by username, link or invite link, and save it in the DB."""
    from telethon.tl.functions.channels import JoinChannelRequest
    # Clean the channel_url (remove t.me/, @, etc.)
    cleaned = channel_url.strip()
    if "t.me/" in cleaned:
        cleaned = cleaned.split("t.me/")[-1]
    if cleaned.startswith("@"):
        cleaned = cleaned[1:]

    entity = await client.get_entity(cleaned)
    await client(JoinChannelRequest(entity))
    
    # Sync this specific joined chat so it shows in the DB
    from telethon.tl.types import Channel as TgChannel, Chat as TgChat, User as TgUser
    chat_type = _chat_type(entity)
    
    # Telethon channel IDs are usually positive, but in dialogs they are stored as negative (e.g. -100xxx)
    # Let's format the ID to match Telethon dialog ID format so it matches sync_chats
    from telethon.utils import get_peer_id
    peer_id = get_peer_id(entity)
    
    values = {
        "telegram_account_id": account.id,
        "telegram_chat_id": peer_id,
        "title": getattr(entity, "title", _display_name(entity)),
        "chat_type": chat_type,
        "username": getattr(entity, "username", None),
        "unread_count": 0,
        "last_message_date": datetime.now(UTC),
        "is_subscribed": True,
        "metadata_json": {
            "participants_count": getattr(entity, "participants_count", None),
        },
        "synced_at": datetime.now(UTC),
    }

    stmt = insert(TelegramChat).values(**values).on_conflict_do_update(
        constraint="uq_telegram_chats_account_chat",
        set_={
            "title": values["title"],
            "chat_type": values["chat_type"],
            "username": values["username"],
            "is_subscribed": values["is_subscribed"],
            "metadata_json": values["metadata_json"],
            "synced_at": values["synced_at"],
        },
    )
    db.execute(stmt)
    db.commit()
    
    # Re-fetch the saved chat ID
    saved_chat = db.query(TelegramChat).filter(
        TelegramChat.telegram_account_id == account.id,
        TelegramChat.telegram_chat_id == peer_id
    ).first()
    
    return {"status": "joined", "chat_id": saved_chat.id if saved_chat else None}


async def leave_channel(client: TelegramClient, telegram_chat_id: int) -> dict:
    """Leave a channel/group."""
    from telethon.tl.functions.channels import LeaveChannelRequest
    entity = await client.get_entity(telegram_chat_id)
    await client(LeaveChannelRequest(entity))
    return {"status": "left"}


# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════


def _chat_type(entity: Any) -> str:
    if isinstance(entity, TgChannel):
        return "channel" if entity.broadcast else "supergroup"
    if isinstance(entity, TgChat):
        return "group"
    if isinstance(entity, TgUser):
        return "user"
    return "unknown"


def _display_name(user: Any) -> str:
    parts = []
    if getattr(user, "first_name", None):
        parts.append(user.first_name)
    if getattr(user, "last_name", None):
        parts.append(user.last_name)
    return " ".join(parts) or getattr(user, "username", None) or str(user.id)


def _serialize_message(message: Any) -> dict:
    try:
        return json.loads(json.dumps(message.to_dict(), default=str))
    except Exception:
        return {}


def _serialize_reactions(reactions: Any) -> dict | None:
    if not reactions:
        return None
    try:
        return json.loads(json.dumps(reactions.to_dict(), default=str))
    except Exception:
        return None


def _store_message(db: Session, chat: TelegramChat, message: Any) -> None:
    if not message.date:
        return

    sender = message.sender
    sender_name = _display_name(sender) if sender else None
    sender_id = getattr(sender, "id", None)

    values = {
        "chat_id": chat.id,
        "telegram_message_id": message.id,
        "sender_name": sender_name,
        "sender_id": sender_id,
        "message_text": message.message,
        "message_date": message.date.astimezone(UTC) if message.date.tzinfo else message.date,
        "raw_payload": _serialize_message(message),
        "views": getattr(message, "views", None),
        "forwards": getattr(message, "forwards", None),
        "reactions": _serialize_reactions(getattr(message, "reactions", None)),
    }

    stmt = insert(TelegramMessage).values(**values).on_conflict_do_update(
        constraint="uq_telegram_messages_chat_msg",
        set_={
            "message_text": values["message_text"],
            "sender_name": values["sender_name"],
            "sender_id": values["sender_id"],
            "raw_payload": values["raw_payload"],
            "views": values["views"],
            "forwards": values["forwards"],
            "reactions": values["reactions"],
        },
    )
    db.execute(stmt)
