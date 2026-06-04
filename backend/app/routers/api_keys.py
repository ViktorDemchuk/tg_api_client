from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import audit_log, get_current_user
from app.models import ApiKey, User
from app.schemas import ApiKeyCreate, ApiKeyCreatedRead, ApiKeyRead
from app.security import generate_api_key

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyRead])
def list_api_keys(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ApiKeyRead]:
    """List all API keys for the current user."""
    keys = list(db.scalars(
        select(ApiKey)
        .where(ApiKey.user_id == user.id)
        .order_by(ApiKey.created_at.desc())
    ))
    return [ApiKeyRead.model_validate(k) for k in keys]


@router.post("", response_model=ApiKeyCreatedRead, status_code=201)
def create_api_key(
    payload: ApiKeyCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiKeyCreatedRead:
    """Create a new API key. The full key is returned ONLY in this response."""
    raw_key, key_hash, key_prefix = generate_api_key()

    api_key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=payload.name,
    )
    db.add(api_key)

    audit_log(
        db, user.id, "api_key.create",
        target_type="api_key", target_id=key_prefix,
        details={"name": payload.name},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(api_key)

    return ApiKeyCreatedRead(
        id=api_key.id,
        user_id=api_key.user_id,
        key_prefix=api_key.key_prefix,
        name=api_key.name,
        is_active=api_key.is_active,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        api_key=raw_key,
    )


@router.delete("/{key_id}", status_code=204)
def revoke_api_key(
    key_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Revoke (delete) an API key."""
    api_key = db.get(ApiKey, key_id)
    if not api_key or api_key.user_id != user.id:
        raise HTTPException(status_code=404, detail="API key not found")

    audit_log(
        db, user.id, "api_key.revoke",
        target_type="api_key", target_id=api_key.key_prefix,
        ip_address=request.client.host if request.client else None,
    )
    db.delete(api_key)
    db.commit()
