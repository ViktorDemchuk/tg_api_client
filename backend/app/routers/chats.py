import asyncio
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import audit_log, get_current_user, verify_account_ownership, verify_active_account
from app.models import (
    TelegramChat,
    TelegramCommand,
    TelegramCommandStatus,
    TelegramMessage,
    User,
)
from app.schemas import SendMessageRequest, SendMessageResult, TelegramChatRead, TelegramMessageRead, JoinChannelRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram/accounts/{account_id}", tags=["chats"])


async def _run_command(
    db: Session,
    account_id: int,
    command_name: str,
    payload: dict | None = None,
    timeout_seconds: int = 60,
) -> dict:
    """Queue a command for the worker and poll for result."""
    cmd = TelegramCommand(
        telegram_account_id=account_id,
        command=command_name,
        payload=payload or {},
    )
    db.add(cmd)
    db.commit()
    db.refresh(cmd)

    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        db.refresh(cmd)
        if cmd.status == TelegramCommandStatus.succeeded:
            return cmd.result or {}
        if cmd.status == TelegramCommandStatus.failed:
            raise HTTPException(status_code=400, detail=cmd.error or "Command failed")
        await asyncio.sleep(0.5)
    raise HTTPException(status_code=504, detail="Worker did not respond in time")


# ═══════════════════════════════════════════════════════════
#  CHATS
# ═══════════════════════════════════════════════════════════


@router.get("/chats", response_model=list[TelegramChatRead])
def list_chats(
    account_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TelegramChatRead]:
    """List cached chats for a Telegram account."""
    verify_account_ownership(db, user, account_id)
    chats = list(db.scalars(
        select(TelegramChat)
        .where(TelegramChat.telegram_account_id == account_id)
        .order_by(TelegramChat.last_message_date.desc().nulls_last())
    ))
    return [TelegramChatRead.model_validate(c) for c in chats]


@router.post("/chats/sync", response_model=list[TelegramChatRead])
async def sync_chats(
    account_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TelegramChatRead]:
    """Force sync chat list from Telegram."""
    verify_active_account(db, user, account_id)

    audit_log(
        db, user.id, "telegram.sync_chats",
        target_type="telegram_account", target_id=str(account_id),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    await _run_command(db, account_id, "sync_chats", timeout_seconds=90)

    # Re-fetch from DB after sync
    chats = list(db.scalars(
        select(TelegramChat)
        .where(TelegramChat.telegram_account_id == account_id)
        .order_by(TelegramChat.last_message_date.desc().nulls_last())
    ))
    return [TelegramChatRead.model_validate(c) for c in chats]


# ═══════════════════════════════════════════════════════════
#  MESSAGES
# ═══════════════════════════════════════════════════════════


@router.get("/chats/{chat_id}/messages", response_model=list[TelegramMessageRead])
def list_messages(
    account_id: int,
    chat_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    since: datetime | None = Query(default=None, description="Only fetch messages newer than this datetime"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TelegramMessageRead]:
    """Get cached messages from a chat."""
    verify_account_ownership(db, user, account_id)

    # Verify chat belongs to this account
    chat = db.get(TelegramChat, chat_id)
    if not chat or chat.telegram_account_id != account_id:
        raise HTTPException(status_code=404, detail="Chat not found")

    query = select(TelegramMessage).where(TelegramMessage.chat_id == chat_id)
    if since:
        query = query.where(TelegramMessage.message_date >= since)
    query = query.order_by(TelegramMessage.message_date.desc()).limit(limit).offset(offset)
    
    messages = list(db.scalars(query))
    return [TelegramMessageRead.model_validate(m) for m in messages]


@router.post("/chats/{chat_id}/send", response_model=SendMessageResult)
async def send_message(
    account_id: int,
    chat_id: int,
    payload: SendMessageRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SendMessageResult:
    """Send a message to a chat via the Telegram account."""
    verify_active_account(db, user, account_id)

    chat = db.get(TelegramChat, chat_id)
    if not chat or chat.telegram_account_id != account_id:
        raise HTTPException(status_code=404, detail="Chat not found")

    audit_log(
        db, user.id, "telegram.send_message",
        target_type="telegram_chat", target_id=str(chat_id),
        details={"account_id": account_id, "text_length": len(payload.text)},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    result = await _run_command(
        db, account_id, "send_message",
        {"telegram_chat_id": chat.telegram_chat_id, "text": payload.text},
    )
    return SendMessageResult(
        status=result.get("status", "sent"),
        telegram_message_id=result.get("telegram_message_id"),
    )


# ═══════════════════════════════════════════════════════════
#  CHANNEL JOIN / LEAVE
# ═══════════════════════════════════════════════════════════


@router.post("/channels/{chat_id}/join")
async def join_channel(
    account_id: int,
    chat_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Subscribe to a channel."""
    verify_active_account(db, user, account_id)
    chat = db.get(TelegramChat, chat_id)
    if not chat or chat.telegram_account_id != account_id:
        raise HTTPException(status_code=404, detail="Chat not found")

    audit_log(
        db, user.id, "telegram.join_channel",
        target_type="telegram_chat", target_id=str(chat_id),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    result = await _run_command(
        db, account_id, "join_channel",
        {"telegram_chat_id": chat.telegram_chat_id},
    )
    return {"status": result.get("status", "joined")}


@router.post("/channels/{chat_id}/leave")
async def leave_channel(
    account_id: int,
    chat_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Unsubscribe from a channel."""
    verify_active_account(db, user, account_id)
    chat = db.get(TelegramChat, chat_id)
    if not chat or chat.telegram_account_id != account_id:
        raise HTTPException(status_code=404, detail="Chat not found")

    audit_log(
        db, user.id, "telegram.leave_channel",
        target_type="telegram_chat", target_id=str(chat_id),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    result = await _run_command(
        db, account_id, "leave_channel",
        {"telegram_chat_id": chat.telegram_chat_id},
    )
    return {"status": result.get("status", "left")}


@router.post("/channels/join")
async def join_channel_by_url(
    account_id: int,
    payload: JoinChannelRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Subscribe to a new channel/group by username or link."""
    verify_active_account(db, user, account_id)

    audit_log(
        db, user.id, "telegram.join_channel_by_url",
        target_type="telegram_account", target_id=str(account_id),
        details={"channel_url": payload.channel_url},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    result = await _run_command(
        db, account_id, "join_channel",
        {"channel_url": payload.channel_url},
    )
    return result
