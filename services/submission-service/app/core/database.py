from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .settings import settings


def _connect_args(url: str) -> dict:
    """psycopg2 connect args: bound the TCP connect and every statement so a
    slow/partitioned database fails fast instead of pinning a worker."""
    if url.startswith("postgresql"):
        return {
            "connect_timeout": settings.db_connect_timeout,
            "options": f"-c statement_timeout={settings.db_statement_timeout_ms}",
        }
    return {}


# Bounded pool that fails fast under saturation and recycles idle connections.
# Pool tuning is applied only for Postgres so SQLite (tests) keeps its defaults.
_engine_kwargs: dict = {
    "pool_pre_ping": True,
    "future": True,
    "connect_args": _connect_args(settings.database_url),
}
if settings.database_url.startswith("postgresql"):
    _engine_kwargs.update(
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
    )

engine = create_engine(settings.database_url, **_engine_kwargs)
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


def database_ready() -> bool:
    """Cheap connectivity check (SELECT 1) for the readiness probe."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
