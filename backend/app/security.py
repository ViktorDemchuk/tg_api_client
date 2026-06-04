import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from cryptography.fernet import Fernet

from app.config import settings

# ═══════════════════════════════════════════════════════════
#  PASSWORD HASHING (bcrypt)
# ═══════════════════════════════════════════════════════════


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


# ═══════════════════════════════════════════════════════════
#  JWT
# ═══════════════════════════════════════════════════════════


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


# ═══════════════════════════════════════════════════════════
#  SESSION ENCRYPTION (Fernet)
# ═══════════════════════════════════════════════════════════

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.session_encryption_key
        if not key:
            raise RuntimeError(
                "SESSION_ENCRYPTION_KEY is required. Generate one with: "
                "python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\""
            )
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def validate_session_encryption_key() -> None:
    """Fail fast at startup if the configured Fernet key is missing or invalid."""
    _get_fernet()


def encrypt_session(session_string: str) -> str:
    return _get_fernet().encrypt(session_string.encode()).decode()


def decrypt_session(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()


# ═══════════════════════════════════════════════════════════
#  API KEYS
# ═══════════════════════════════════════════════════════════


def generate_api_key() -> tuple[str, str, str]:
    """Generate an API key. Returns (raw_key, key_hash, key_prefix)."""
    raw_key = f"tgc_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:8]
    return raw_key, key_hash, key_prefix


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()
