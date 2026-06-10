import os

os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret")

import uuid

import pytest
from app.core.security import get_authenticated_user, require_administrator
from app.core.settings import settings
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt


def _make_token(*, is_admin: bool = False) -> str:
    return jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "email": "u@example.com",
            "is_admin": is_admin,
            "exp": 9999999999,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def test_authenticated_user_ok():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=_make_token())
    user = get_authenticated_user(creds)
    assert user.email == "u@example.com"
    assert user.is_admin is False


def test_require_admin_blocks_non_admin():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=_make_token(is_admin=False))
    user = get_authenticated_user(creds)
    with pytest.raises(HTTPException) as exc:
        require_administrator(user)
    assert exc.value.status_code == 403


def test_require_admin_allows_admin():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=_make_token(is_admin=True))
    user = get_authenticated_user(creds)
    assert require_administrator(user) is user


def test_invalid_token_rejected():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not.a.jwt")
    with pytest.raises(HTTPException) as exc:
        get_authenticated_user(creds)
    assert exc.value.status_code == 401
