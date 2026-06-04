from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import audit_log, get_admin_user
from app.models import (
    AuditLog,
    TelegramAccount,
    TelegramAccountStatus,
    TelegramChat,
    TelegramMessage,
    User,
)
from app.schemas import (
    AdminDisableRequest,
    AdminStatsRead,
    AdminUserRead,
    AuditLogRead,
    TelegramAccountRead,
    UserRead,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserRead])
def list_users(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    """List all registered users."""
    users = list(db.scalars(select(User).order_by(User.created_at.desc())))
    return [UserRead.model_validate(u) for u in users]


@router.get("/users/{user_id}", response_model=AdminUserRead)
def get_user_detail(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> AdminUserRead:
    """Get user detail with their Telegram accounts."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    accounts = list(db.scalars(
        select(TelegramAccount).where(TelegramAccount.user_id == user_id)
    ))
    return AdminUserRead(
        **UserRead.model_validate(user).model_dump(),
        telegram_accounts=[TelegramAccountRead.model_validate(a) for a in accounts],
    )


@router.post("/users/{user_id}/disable", response_model=UserRead)
def toggle_user(
    user_id: int,
    payload: AdminDisableRequest,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> UserRead:
    """Enable or disable a user."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot disable yourself")

    user.is_active = payload.is_active
    audit_log(
        db, admin.id, "admin.toggle_user",
        target_type="user", target_id=str(user_id),
        details={"is_active": payload.is_active},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a user and all their associated data (Telegram accounts, sessions, chats, messages)."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    audit_log(
        db, admin.id, "admin.delete_user",
        target_type="user", target_id=str(user_id),
        details={"username": user.username, "email": user.email},
        ip_address=request.client.host if request.client else None,
    )
    db.delete(user)
    db.commit()


@router.get("/accounts", response_model=list[TelegramAccountRead])
def list_all_accounts(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> list[TelegramAccountRead]:
    """List all Telegram accounts in the system."""
    accounts = list(db.scalars(
        select(TelegramAccount).order_by(TelegramAccount.created_at.desc())
    ))
    return [TelegramAccountRead.model_validate(a) for a in accounts]


@router.post("/accounts/{account_id}/disable", response_model=TelegramAccountRead)
def toggle_account(
    account_id: int,
    payload: AdminDisableRequest,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> TelegramAccountRead:
    """Enable or disable a Telegram account."""
    account = db.get(TelegramAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.is_active = payload.is_active
    audit_log(
        db, admin.id, "admin.toggle_account",
        target_type="telegram_account", target_id=str(account_id),
        details={"is_active": payload.is_active},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(account)
    return TelegramAccountRead.model_validate(account)


@router.delete("/accounts/{account_id}", status_code=204)
def delete_account(
    account_id: int,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a Telegram account and all its associated session and cached data."""
    account = db.get(TelegramAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    audit_log(
        db, admin.id, "admin.delete_account",
        target_type="telegram_account", target_id=str(account_id),
        details={"phone": account.phone},
        ip_address=request.client.host if request.client else None,
    )
    db.delete(account)
    db.commit()


@router.get("/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    action: str | None = None,
    user_id: int | None = None,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> list[AuditLogRead]:
    """List audit logs with optional filtering."""
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    if action:
        query = query.where(AuditLog.action == action)
    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    logs = list(db.scalars(query))
    return [AuditLogRead.model_validate(log) for log in logs]


@router.get("/stats", response_model=AdminStatsRead)
def admin_stats(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> AdminStatsRead:
    """System-wide statistics."""
    return AdminStatsRead(
        total_users=db.scalar(select(func.count(User.id))) or 0,
        active_users=db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0,
        total_telegram_accounts=db.scalar(select(func.count(TelegramAccount.id))) or 0,
        authorized_accounts=db.scalar(
            select(func.count(TelegramAccount.id)).where(
                TelegramAccount.status == TelegramAccountStatus.authorized
            )
        ) or 0,
        total_chats=db.scalar(select(func.count(TelegramChat.id))) or 0,
        total_messages=db.scalar(select(func.count(TelegramMessage.id))) or 0,
    )
