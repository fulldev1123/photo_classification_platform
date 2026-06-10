import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import UserAccount


class UserRepository:
    """Data-access boundary for the ``users`` table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_email(self, email: str) -> UserAccount | None:
        statement = select(UserAccount).where(UserAccount.email == email.lower())
        return self._session.execute(statement).scalar_one_or_none()

    def find_by_id(self, account_id: uuid.UUID | str) -> UserAccount | None:
        return self._session.get(UserAccount, account_id)

    def add(self, account: UserAccount) -> UserAccount:
        self._session.add(account)
        self._session.commit()
        self._session.refresh(account)
        return account
