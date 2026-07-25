"""SQLAlchemy engine, session, and bootstrap helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import Config
from .models import Base


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def init_engine(config: Config) -> None:
    """Initialise the global engine and session factory."""

    global _engine, _SessionLocal
    kwargs = {"future": True}
    if config.database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    _engine = create_engine(config.database_url, **kwargs)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """Create all tables. Idempotent."""

    if _engine is None:
        raise RuntimeError("engine not initialised; call init_engine first")
    Base.metadata.create_all(_engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""

    if _SessionLocal is None:
        raise RuntimeError("session factory not initialised")
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def upsert_user(username: str, password_hash: str, display_name: str | None = None) -> None:
    """Create or update the single operator user."""

    from .models import User

    if _SessionLocal is None:
        raise RuntimeError("session factory not initialised")
    with session_scope() as s:
        existing = s.query(User).filter(User.username == username).one_or_none()
        if existing is None:
            s.add(User(username=username, password_hash=password_hash, display_name=display_name))
        else:
            existing.password_hash = password_hash
            if display_name is not None:
                existing.display_name = display_name
