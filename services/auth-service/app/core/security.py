from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from .settings import settings

password_hasher = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(raw_password: str) -> str:
    """Return a bcrypt digest for a plaintext password."""
    return password_hasher.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored bcrypt digest."""
    return password_hasher.verify(raw_password, password_hash)


def issue_access_token(*, subject: str, email: str, is_admin: bool) -> tuple[str, int]:
    """Mint a signed JWT for an account. Returns ``(token, ttl_seconds)``."""
    ttl_seconds = settings.access_token_expires_minutes * 60
    claims: dict[str, Any] = {
        "sub": subject,
        "email": email,
        "is_admin": is_admin,
        "exp": datetime.now(tz=UTC) + timedelta(seconds=ttl_seconds),
        "iss": settings.service_name,
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, ttl_seconds


def decode_access_token(token: str) -> dict[str, Any]:
    """Validate a JWT's signature/expiry and return its claims."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError(f"invalid token: {exc}") from exc
