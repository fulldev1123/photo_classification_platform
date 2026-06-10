import os

os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_auth.db")

import pytest  # noqa: E402
from app.core.security import (  # noqa: E402
    decode_access_token,
    hash_password,
    issue_access_token,
    verify_password,
)


def test_password_hash_roundtrip():
    digest = hash_password("hunter2hunter2")
    assert digest != "hunter2hunter2"
    assert verify_password("hunter2hunter2", digest)
    assert not verify_password("wrong", digest)


def test_access_token_roundtrip():
    token, expires_in = issue_access_token(
        subject="00000000-0000-0000-0000-000000000001",
        email="a@b.com",
        is_admin=False,
    )
    assert expires_in > 0
    claims = decode_access_token(token)
    assert claims["sub"] == "00000000-0000-0000-0000-000000000001"
    assert claims["email"] == "a@b.com"
    assert claims["is_admin"] is False


def test_access_token_rejects_tampering():
    token, _ = issue_access_token(subject="x", email="a@b.com", is_admin=False)
    tampered = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    with pytest.raises(ValueError):
        decode_access_token(tampered)
