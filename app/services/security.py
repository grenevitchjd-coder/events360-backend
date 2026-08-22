import re
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_SPECIAL_CHAR_RE = re.compile(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;'/`~]")
_NUMBER_RE = re.compile(r"\d")


def validate_password_policy(password: str) -> None:
    """
    Enforced server-side (not just frontend) for both User and PlatformAdmin
    accounts, per architecture doc: min 8 chars, 1 number, 1 special char.
    Raises ValueError with a clear message if the policy isn't met.
    """
    if len(password) < settings.password_min_length:
        raise ValueError(f"Password must be at least {settings.password_min_length} characters long.")
    if not _NUMBER_RE.search(password):
        raise ValueError("Password must contain at least 1 number.")
    if not _SPECIAL_CHAR_RE.search(password):
        raise ValueError("Password must contain at least 1 special character.")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(subject: str, extra_claims: dict, expires_minutes: int | None = None) -> str:
    """
    subject: typically the account's UUID as a string.
    extra_claims: e.g. {"type": "user", "org_id": "...", "role": "org_owner"}
                  or {"type": "platform_admin", "role": "superadmin"}
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.jwt_expire_minutes
    )
    to_encode = {"sub": subject, "exp": expire, **extra_claims}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Raises JWTError if invalid/expired — callers should catch and return 401."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])