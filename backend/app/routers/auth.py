from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import audit_log, get_current_user
from app.models import User, UserRole
from app.schemas import TokenRead, UserLogin, UserRead, UserRegister, UserUpdate
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
def register(
    payload: UserRegister,
    request: Request,
    db: Session = Depends(get_db),
) -> UserRead:
    """Register a new user account."""
    # Check uniqueness
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=UserRole.user,
    )
    db.add(user)
    db.flush()

    audit_log(
        db, user.id, "user.register",
        target_type="user", target_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenRead)
def login(
    payload: UserLogin,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenRead:
    """Authenticate and receive a JWT token."""
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})

    audit_log(
        db, user.id, "user.login",
        target_type="user", target_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return TokenRead(access_token=token)


@router.get("/me", response_model=UserRead)
def get_profile(user: User = Depends(get_current_user)) -> UserRead:
    """Get current user profile."""
    return UserRead.model_validate(user)


@router.put("/me", response_model=UserRead)
def update_profile(
    payload: UserUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    """Update current user profile."""
    fields_updated = []

    if payload.username is not None:
        existing = db.scalar(
            select(User).where(User.username == payload.username, User.id != user.id)
        )
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        user.username = payload.username
        fields_updated.append("username")

    if payload.email is not None:
        existing = db.scalar(
            select(User).where(User.email == payload.email, User.id != user.id)
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = payload.email
        fields_updated.append("email")

    if payload.password is not None:
        user.hashed_password = hash_password(payload.password)
        fields_updated.append("password")

    if fields_updated:
        audit_log(
            db,
            user.id,
            "user.update_profile",
            target_type="user",
            target_id=str(user.id),
            details={"fields": fields_updated},
            ip_address=request.client.host if request.client else None,
        )

    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)
