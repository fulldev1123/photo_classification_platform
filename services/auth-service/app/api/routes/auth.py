from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from ...core.database import get_session
from ...core.security import (
    decode_access_token,
    hash_password,
    issue_access_token,
    verify_password,
)
from ...core.settings import settings
from ...models import UserAccount
from ...repositories import UserRepository
from ...schemas import (
    AccessTokenResponse,
    AccountResponse,
    LoginRequest,
    RegistrationRequest,
    TokenClaims,
)

router = APIRouter(tags=["auth"])
rate_limiter = Limiter(
    key_func=get_remote_address, storage_uri=settings.rate_limit_storage_uri
)
bearer_scheme = HTTPBearer(auto_error=True)


@router.post(
    "/register",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
@rate_limiter.limit(settings.register_rate_limit)
def register(
    request: Request,
    body: RegistrationRequest,
    session: Session = Depends(get_session),
):
    accounts = UserRepository(session)
    if accounts.find_by_email(body.email):
        raise HTTPException(status_code=409, detail="email already registered")
    account = UserAccount(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        is_admin=False,
    )
    return accounts.add(account)


@router.post("/login", response_model=AccessTokenResponse, summary="Log in and receive a JWT")
@rate_limiter.limit(settings.login_rate_limit)
def login(
    request: Request,
    body: LoginRequest,
    session: Session = Depends(get_session),
):
    account = UserRepository(session).find_by_email(body.email)
    if not account or not verify_password(body.password, account.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    if not account.is_active:
        raise HTTPException(status_code=403, detail="account disabled")
    token, expires_in = issue_access_token(
        subject=str(account.id), email=account.email, is_admin=account.is_admin
    )
    return AccessTokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=AccountResponse, summary="Return the current account")
def current_account(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: Session = Depends(get_session),
):
    try:
        claims = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc
    account = UserRepository(session).find_by_id(claims["sub"])
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    return account


@router.post("/introspect", response_model=TokenClaims, summary="Validate a token (for peers)")
def introspect(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """Validate a token on behalf of another service.

    Peers can also verify locally with the shared ``JWT_SECRET``; this endpoint
    exists for explicit, centralized validation / revocation flows.
    """
    try:
        claims = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc
    return TokenClaims(**claims)
