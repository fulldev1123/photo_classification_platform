from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .settings import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model in this service."""


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped database session."""
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()
