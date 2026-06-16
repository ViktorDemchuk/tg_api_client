import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import (
    audit_log,
    get_current_user,
    resolve_account_by_tg_id,
    resolve_active_account_by_tg_id,
    verify_account_ownership,
    verify_active_account,
)
from app.models import (
    TelegramAccount,
    TelegramAccountStatus,
    TelegramCommand,
    TelegramCommandStatus,
    TelegramSession,
    User,
)
from app.schemas import (
    TelegramAccountCreate,
    TelegramAccountRead,
    TelegramAuthResult,
    TelegramSubmitCodeRequest,
    TelegramSubmitPasswordRequest,
    TelegramSessionExport,
)
from app.security import decrypt_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["telegram"])
pending_router = APIRouter(prefix="/telegram/pending", tags=["telegram-auth"])


# ═══════════════════════════════════════════════════════════
#  ACCOUNT CRUD
# ═══════════════════════════════════════════════════════════


@router.get("/accounts", response_model=list[TelegramAccountRead])
def list_accounts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TelegramAccountRead]:
    """List all Telegram accounts owned by the current user."""
    accounts = list(db.scalars(
        select(TelegramAccount)
        .where(TelegramAccount.user_id == user.id)
        .order_by(TelegramAccount.created_at.desc())
    ))
    return [TelegramAccountRead.model_validate(a) for a in accounts]


@router.post("/accounts", response_model=TelegramAccountRead, status_code=201)
def add_account(
    payload: TelegramAccountCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TelegramAccountRead:
    """Add a new Telegram account by phone number."""
    # Check limits
    count = db.scalar(
        select(func.count(TelegramAccount.id)).where(TelegramAccount.user_id == user.id)
    ) or 0
    if count >= settings.max_accounts_per_user:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.max_accounts_per_user} accounts per user",
        )

    # Check for duplicate phone
    existing = db.scalar(
        select(TelegramAccount).where(
            TelegramAccount.user_id == user.id,
            TelegramAccount.phone == payload.phone,
        )
    )
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already connected")

    account = TelegramAccount(
        user_id=user.id,
        phone=payload.phone,
        status=TelegramAccountStatus.pending,
    )
    db.add(account)
    db.flush()

    # Create empty session record
    session = TelegramSession(telegram_account_id=account.id)
    db.add(session)

    audit_log(
        db, user.id, "telegram.add_account",
        target_type="telegram_account", target_id=str(account.id),
        details={"phone": payload.phone},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(account)
    return TelegramAccountRead.model_validate(account)


@router.get("/accounts/{tg_user_id}", response_model=TelegramAccountRead)
def get_account(
    tg_user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TelegramAccountRead:
    """Get a specific Telegram account by its Telegram user ID."""
    account = resolve_account_by_tg_id(db, user, tg_user_id)
    return TelegramAccountRead.model_validate(account)


@router.delete("/accounts/{tg_user_id}", status_code=204)
def delete_account(
    tg_user_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove a Telegram account and its session data."""
    account = resolve_account_by_tg_id(db, user, tg_user_id)
    audit_log(
        db, user.id, "telegram.delete_account",
        target_type="telegram_account", target_id=str(account.id),
        details={"phone": account.phone},
        ip_address=request.client.host if request.client else None,
    )
    db.delete(account)
    db.commit()


@router.get("/accounts/{tg_user_id}/status", response_model=TelegramAccountRead)
def account_status(
    tg_user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TelegramAccountRead:
    """Get connection status for a Telegram account."""
    account = resolve_account_by_tg_id(db, user, tg_user_id)
    return TelegramAccountRead.model_validate(account)


# ═══════════════════════════════════════════════════════════
#  TELEGRAM AUTH FLOW (via command queue, uses local IDs)
# ═══════════════════════════════════════════════════════════


async def _run_telegram_command(
    db: Session,
    account_id: int,
    command_name: str,
    payload: dict | None = None,
    timeout_seconds: int = 45,
) -> dict:
    """Queue a command for the worker and wait for the result."""
    command = TelegramCommand(
        telegram_account_id=account_id,
        command=command_name,
        payload=payload or {},
    )
    db.add(command)
    db.commit()
    db.refresh(command)

    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        db.refresh(command)
        if command.status == TelegramCommandStatus.succeeded:
            return command.result or {}
        if command.status == TelegramCommandStatus.failed:
            raise HTTPException(status_code=400, detail=command.error or "Telegram command failed")
        await asyncio.sleep(0.5)
    raise HTTPException(status_code=504, detail="Telegram worker did not respond in time")


@pending_router.post("/{account_id}/send-code", response_model=TelegramAuthResult)
async def send_code(
    account_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TelegramAuthResult:
    """Request a Telegram login code for the account."""
    account = verify_active_account(db, user, account_id)

    audit_log(
        db, user.id, "telegram.send_code",
        target_type="telegram_account", target_id=str(account.id),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    result = await _run_telegram_command(db, account.id, "send_code", {"phone": account.phone})
    return TelegramAuthResult(
        status=result.get("status", "code_sent"),
        authorized=bool(result.get("authorized")),
        phone=account.phone,
    )


@pending_router.post("/{account_id}/submit-code", response_model=TelegramAuthResult)
async def submit_code(
    account_id: int,
    payload: TelegramSubmitCodeRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TelegramAuthResult:
    """Submit the Telegram login code (and optional 2FA password)."""
    account = verify_active_account(db, user, account_id)

    audit_log(
        db, user.id, "telegram.submit_code",
        target_type="telegram_account", target_id=str(account.id),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    result = await _run_telegram_command(
        db, account.id, "submit_code",
        {"phone": account.phone, "code": payload.code, "password": payload.password},
    )
    return TelegramAuthResult(
        status=result.get("status", "not_authorized"),
        authorized=bool(result.get("authorized")),
        needs_password=bool(result.get("needs_password")),
        phone=account.phone,
    )


@router.post("/accounts/qr", response_model=TelegramAccountRead, status_code=201)
def add_account_qr(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TelegramAccountRead:
    """Add a new pending Telegram account for QR login."""
    count = db.scalar(
        select(func.count(TelegramAccount.id)).where(TelegramAccount.user_id == user.id)
    ) or 0
    if count >= settings.max_accounts_per_user:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.max_accounts_per_user} accounts per user",
        )

    import secrets
    placeholder_phone = f"+QR_PENDING_{secrets.token_hex(8)}"

    account = TelegramAccount(
        user_id=user.id,
        phone=placeholder_phone,
        status=TelegramAccountStatus.pending,
    )
    db.add(account)
    db.flush()

    # Create empty session record
    session = TelegramSession(telegram_account_id=account.id)
    db.add(session)

    audit_log(
        db, user.id, "telegram.add_account_qr",
        target_type="telegram_account", target_id=str(account.id),
        details={"phone": placeholder_phone},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(account)
    return TelegramAccountRead.model_validate(account)


@pending_router.post("/{account_id}/qr-request", response_model=TelegramAuthResult)
async def qr_request(
    account_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TelegramAuthResult:
    """Request a QR code login link for the account."""
    account = verify_active_account(db, user, account_id)

    audit_log(
        db, user.id, "telegram.qr_request",
        target_type="telegram_account", target_id=str(account.id),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    result = await _run_telegram_command(db, account.id, "request_qr", timeout_seconds=30)
    return TelegramAuthResult(
        status=result.get("status", "pending"),
        authorized=bool(result.get("authorized")),
        qr_link=result.get("qr_link"),
        account_id=account.id,
    )


@pending_router.post("/{account_id}/qr-wait", response_model=TelegramAuthResult)
async def qr_wait(
    account_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TelegramAuthResult:
    """Wait for the QR code to be scanned."""
    account = verify_active_account(db, user, account_id)

    result = await _run_telegram_command(db, account.id, "wait_qr", timeout_seconds=15)
    final_account_id = result.get("account_id", account.id)

    return TelegramAuthResult(
        status=result.get("status", "pending"),
        authorized=bool(result.get("authorized")),
        needs_password=bool(result.get("needs_password")),
        phone=result.get("phone"),
        account_id=final_account_id,
    )


@pending_router.post("/{account_id}/qr-password", response_model=TelegramAuthResult)
async def qr_password(
    account_id: int,
    payload: TelegramSubmitPasswordRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TelegramAuthResult:
    """Submit the 2FA password to complete the QR code login."""
    account = verify_active_account(db, user, account_id)

    audit_log(
        db, user.id, "telegram.qr_password",
        target_type="telegram_account", target_id=str(account.id),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    result = await _run_telegram_command(
        db, account.id, "submit_password",
        {"password": payload.password},
    )
    final_account_id = result.get("account_id", account.id)

    return TelegramAuthResult(
        status=result.get("status", "not_authorized"),
        authorized=bool(result.get("authorized")),
        phone=result.get("phone"),
        account_id=final_account_id,
    )


# ═══════════════════════════════════════════════════════════
#  POST-AUTH OPERATIONS (use Telegram user IDs)
# ═══════════════════════════════════════════════════════════


@router.post("/accounts/{tg_user_id}/disconnect", response_model=TelegramAccountRead)
def disconnect_account(
    tg_user_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TelegramAccountRead:
    """Disconnect a Telegram account (clear session, mark as disconnected)."""
    account = resolve_active_account_by_tg_id(db, user, tg_user_id)
    account.status = TelegramAccountStatus.disconnected
    if account.session:
        account.session.encrypted_session = None
        account.session.phone_code_hash = None

    audit_log(
        db, user.id, "telegram.disconnect",
        target_type="telegram_account", target_id=str(account.id),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(account)
    return TelegramAccountRead.model_validate(account)


@router.get("/accounts/{tg_user_id}/session", response_model=TelegramSessionExport)
def export_session(
    tg_user_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TelegramSessionExport:
    """Export the decrypted Telegram session string for an account."""
    account = resolve_account_by_tg_id(db, user, tg_user_id)

    session = db.scalar(
        select(TelegramSession).where(TelegramSession.telegram_account_id == account.id)
    )
    session_str = None
    if session and session.encrypted_session:
        try:
            session_str = decrypt_session(session.encrypted_session)
        except Exception as exc:
            err_msg = str(exc) or "Invalid Fernet token. Ensure SESSION_ENCRYPTION_KEY is identical in backend and worker, then restart."
            raise HTTPException(status_code=500, detail=f"Failed to decrypt session key: {err_msg}")

    audit_log(
        db, user.id, "telegram.export_session",
        target_type="telegram_account", target_id=str(account.id),
        details={"phone": account.phone},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    return TelegramSessionExport(phone=account.phone, session_string=session_str)
