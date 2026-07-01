"""Shared SQLAlchemy database runtime for TTRPG subsystems.

Each TTRPG system (D&D, CoC) instantiates its own ``Database`` with a
system name that determines the default SQLite path under ``~/.sagasmith/``.
"""

from __future__ import annotations

import os
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from nanobot.ttrpg._paths import get_runtime_subdir


class Base(DeclarativeBase):
    """Declarative base shared by all TTRPG domain models."""


def default_database_url(system: str) -> str:
    """Return the configured URL or the instance-local SQLite database URL.

    Env vars checked in order:
      - ``<SYSTEM>_DATABASE_URL`` (e.g. ``DND_DATABASE_URL``, ``COC7_DATABASE_URL``)
      - ``DATABASE_URL`` (shared fallback)
      - ``~/.sagasmith/<system>/<system>.db`` (default)
    """
    configured = (
        os.environ.get(f"{system.upper()}_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
    )
    if configured:
        return configured
    database_path = get_runtime_subdir(system) / f"{system}.db"
    return f"sqlite+pysqlite:///{database_path.as_posix()}"


class Database:
    """Own a TTRPG database engine and its transactional session factory."""

    def __init__(
        self,
        system: str,
        url: str | None = None,
        *,
        echo: bool = False,
    ) -> None:
        self.system = system
        self.url = url or default_database_url(system)
        connect_args = {"check_same_thread": False} if self.url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(
            self.url,
            connect_args=connect_args,
            pool_pre_ping=True,
            echo=echo,
        )
        if self.engine.dialect.name == "sqlite":
            event.listen(self.engine, "connect", self._enable_sqlite_foreign_keys)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    @staticmethod
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    def create_schema(self, models_module: str) -> None:
        """Create the current schema directly (for tests)."""
        import importlib
        importlib.import_module(models_module)
        Base.metadata.create_all(bind=self.engine)

    def upgrade_schema(self, alembic_config_path: str, revision: str = "head") -> None:
        """Upgrade a persistent database through bundled Alembic migrations."""
        import subprocess
        import sys

        result = subprocess.run(
            [
                sys.executable, "-m", "alembic",
                "-c", alembic_config_path,
                "upgrade", revision,
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "DATABASE_URL": self.url},
        )
        if result.returncode != 0:
            raise RuntimeError(f"Schema migration failed: {result.stderr}")

    def drop_schema(self) -> None:
        """Drop all tables. Intended for isolated tests only."""
        Base.metadata.drop_all(bind=self.engine)

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        """Commit one unit of work, rolling it back if an exception escapes."""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dependency(self) -> Generator[Session, None, None]:
        """Yield a session for dependency-injection frameworks."""
        session = self.session_factory()
        try:
            yield session
        finally:
            session.close()

    def dispose(self) -> None:
        """Release pooled database connections."""
        self.engine.dispose()


def sqlite_database_url(path: str | Path) -> str:
    """Build a SQLAlchemy SQLite URL from a filesystem path."""
    return f"sqlite+pysqlite:///{Path(path).expanduser().resolve().as_posix()}"
