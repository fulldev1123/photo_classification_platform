import logging

from sqlalchemy.exc import IntegrityError

from .core.database import SessionFactory
from .core.security import hash_password
from .core.settings import settings
from .models import UserAccount
from .repositories import UserRepository

logger = logging.getLogger(settings.service_name)


def seed_admin_account() -> None:
    """Create the bootstrap administrator if it does not already exist.

    Tolerant of the multi-replica startup race: if another pod inserts the
    admin first, the unique-email constraint raises IntegrityError, which we
    swallow rather than crash-looping the pod.
    """
    with SessionFactory() as session:
        accounts = UserRepository(session)
        if accounts.find_by_email(settings.admin_email):
            return
        try:
            accounts.add(
                UserAccount(
                    email=settings.admin_email.lower(),
                    password_hash=hash_password(settings.admin_password),
                    is_admin=True,
                )
            )
            logger.info("seeded bootstrap admin: %s", settings.admin_email)
        except IntegrityError:
            session.rollback()
            logger.info("admin already seeded by another replica")
