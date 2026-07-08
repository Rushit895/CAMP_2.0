"""Database engine, session factory, and Base for CAMP2.O persistence.

Defaults to a local SQLite file (zero-config). Point CAMP_DB_URL at Postgres/MariaDB
for a real deployment — nothing else changes.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Default SQLite file lives next to the backend/ package root.
_DEFAULT_DB = f"sqlite:///{(Path(__file__).resolve().parent.parent.parent / 'camp.db').as_posix()}"
DB_URL = os.environ.get("CAMP_DB_URL", _DEFAULT_DB)

# check_same_thread is a SQLite-only knob (safe to pass only for sqlite).
_connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}

engine = create_engine(DB_URL, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Create tables if they don't exist. Import models first so they're registered."""
    from . import models  # noqa: F401  (side-effect: registers mappers on Base)

    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency — yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
