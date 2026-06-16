import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal, engine
from app.models import Base, User, UserRole
from app.routers import admin, api_keys, auth, chats, telegram
from app.security import hash_password, validate_session_encryption_key

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: seed admin user if needed."""
    validate_session_encryption_key()
    _seed_admin()
    yield


def _seed_admin():
    """Create the initial admin user from env vars if no admin exists."""
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.role == UserRole.admin).limit(1))
        if existing:
            return
        admin_user = User(
            email=settings.admin_email,
            username="admin",
            hashed_password=hash_password(settings.admin_password),
            role=UserRole.admin,
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        logger.info("Seeded admin user: %s", settings.admin_email)


app = FastAPI(
    title="TG API Client",
    version="1.0.0",
    root_path=settings.api_root_path,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ──
app.include_router(auth.router)
app.include_router(telegram.router)
app.include_router(telegram.pending_router)
app.include_router(chats.router)
app.include_router(api_keys.router)
app.include_router(admin.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "tg-api-client"}
