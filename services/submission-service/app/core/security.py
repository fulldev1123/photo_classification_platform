import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .settings import settings

bearer_scheme = HTTPBearer(auto_error=True)


@dataclass(frozen=True)
class AuthenticatedUser:
    """The caller identified from a verified bearer token."""

    id: uuid.UUID
    email: str
    is_admin: bool


def _decode_claims(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"invalid token: {exc}") from exc


def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthenticatedUser:
    """Resolve and validate the caller from the ``Authorization`` header."""
    claims = _decode_claims(credentials.credentials)
    try:
        return AuthenticatedUser(
            id=uuid.UUID(claims["sub"]),
            email=claims["email"],
            is_admin=bool(claims.get("is_admin", False)),
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="malformed token") from exc


def require_administrator(
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> AuthenticatedUser:
    """Dependency that rejects non-admin callers with HTTP 403."""
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")
    return user
