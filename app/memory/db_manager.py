"""SQLite database manager for Phase 5.3 Long-Term Memory.

Phase 5.3 - Long-Term Memory & Persistent Memory Foundation
"""

import os
import threading
import time
from pathlib import Path

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from app.config.manager import ConfigurationManager
from app.logging import logger
from app.memory.db_models import Base, SchemaVersionORM


class MemoryDatabaseManager:
    """Manages SQLite engine creation, connection pooling, and schema lifecycle."""

    CURRENT_SCHEMA_VERSION = 1

    def __init__(
        self,
        config_manager: ConfigurationManager | None = None,
        db_path_override: str | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self.config_manager = config_manager or ConfigurationManager()
        self._db_path: str = db_path_override or self._resolve_db_path()
        self._engine = None
        self._session_factory = None
        self._is_initialized = False
        self._last_error: str | None = None

    @property
    def db_path(self) -> str:
        """Resolved SQLite database file path."""
        return self._db_path

    @property
    def is_initialized(self) -> bool:
        """Return True if database engine and schema are ready."""
        with self._lock:
            return self._is_initialized

    def _resolve_db_path(self) -> str:
        """Resolve local application data directory path for SQLite DB file."""
        try:
            settings = self.config_manager.settings
            if (
                hasattr(settings, "long_term_memory")
                and settings.long_term_memory.db_path
            ):
                return settings.long_term_memory.db_path
        except Exception:  # noqa: BLE001
            pass

        # Default Windows LocalAppData location
        local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~/.friday"))
        db_dir = Path(local_app_data) / "Friday" / "memory"
        return str(db_dir / "friday_memory.db")

    def initialize_database(self) -> bool:
        """Initialize SQLite database, parent directories, and SQLAlchemy tables."""
        with self._lock:
            if self._is_initialized:
                return True

            try:
                db_file = Path(self._db_path)
                db_file.parent.mkdir(parents=True, exist_ok=True)

                self._engine = create_engine(
                    f"sqlite:///{self._db_path}",
                    connect_args={"check_same_thread": False},
                    pool_pre_ping=True,
                )

                # Initialize schema
                Base.metadata.create_all(bind=self._engine)

                # Scoped session factory
                session_factory = sessionmaker(bind=self._engine)
                self._session_factory = scoped_session(session_factory)

                # Record/verify schema version
                with self._session_factory() as session:
                    stmt = select(SchemaVersionORM).where(
                        SchemaVersionORM.version == self.CURRENT_SCHEMA_VERSION
                    )
                    v_record = session.scalar(stmt)
                    if not v_record:
                        session.add(
                            SchemaVersionORM(
                                version=self.CURRENT_SCHEMA_VERSION,
                                applied_at=time.time(),
                            )
                        )
                        session.commit()

                self._is_initialized = True
                self._last_error = None
                logger.info(
                    f"MemoryDatabaseManager: Initialized SQLite database at '{self._db_path}'."
                )
                return True

            except Exception as exc:  # noqa: BLE001
                self._last_error = str(exc)
                self._is_initialized = False
                logger.error(
                    f"MemoryDatabaseManager: Failed to initialize SQLite database at '{self._db_path}': {exc}"
                )
                return False

    def get_session(self) -> Session:
        """Acquire a thread-local SQLAlchemy Session instance."""
        if (
            not self._is_initialized or not self._session_factory
        ) and not self.initialize_database():
            raise RuntimeError(f"MemoryDatabaseManager unavailable: {self._last_error}")
        return self._session_factory()

    def is_healthy(self) -> bool:
        """Check connection health using a test SELECT 1 query."""
        if not self._is_initialized or not self._session_factory:
            return False
        try:
            session = self._session_factory()
            session.execute(text("SELECT 1"))
            session.close()
            return True
        except Exception:  # noqa: BLE001
            return False

    def close(self) -> None:
        """Close session factory and dispose of engine."""
        with self._lock:
            if self._session_factory:
                self._session_factory.remove()
                self._session_factory = None
            if self._engine:
                self._engine.dispose()
                self._engine = None
            self._is_initialized = False
