"""Database session management."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.database.models import Base

_engine = None
_session_factory = None


def database_url(path: Path | None = None) -> str:
    settings = get_settings()
    db_path = Path(path) if path else Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def get_engine(db_path: Path | None = None):
    global _engine
    if _engine is None:
        _engine = create_engine(database_url(db_path), connect_args={"check_same_thread": False})
    return _engine


def get_session_factory(db_path: Path | None = None):
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(db_path), expire_on_commit=False)
    return _session_factory


def init_db(db_path: Path | None = None) -> None:
    """Create tables (used when Alembic migrations are not applied)."""
    Base.metadata.create_all(bind=get_engine(db_path))


def reset_db(db_path: Path | None = None) -> None:
    """Drop and recreate all tables (tests/diagnostics)."""
    Base.metadata.drop_all(bind=get_engine(db_path))
    Base.metadata.create_all(bind=get_engine(db_path))


@contextmanager
def session_scope(db_path: Path | None = None) -> Iterator[Session]:
    """Transactional session context: commit on success, rollback on error."""
    Session = get_session_factory(db_path)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
