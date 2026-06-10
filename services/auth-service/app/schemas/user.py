import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegistrationRequest(BaseModel):
    """Payload for ``POST /auth/register``."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Payload for ``POST /auth/login``."""

    email: EmailStr
    password: str


class AccountResponse(BaseModel):
    """Public view of a user account."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    is_admin: bool
    is_active: bool
    created_at: datetime


class AccessTokenResponse(BaseModel):
    """Returned by ``POST /auth/login``."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenClaims(BaseModel):
    """Decoded JWT claims returned by ``POST /auth/introspect``."""

    sub: str
    email: EmailStr
    is_admin: bool
    exp: int
