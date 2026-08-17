"""Repository abstraction and SQLAlchemy repository implementation for Phase 5.3 Long-Term Memory.

Phase 5.3 - Long-Term Memory & Persistent Memory Foundation
"""

import json
import time
from abc import ABC, abstractmethod

from sqlalchemy import func, select

from app.memory.db_manager import MemoryDatabaseManager
from app.memory.db_models import MemoryORM
from app.memory.long_term_models import (
    LongTermMemoryEntry,
    MemoryImportance,
    MemorySource,
    MemoryType,
    SensitivityLevel,
    UserControlState,
)


class IMemoryRepository(ABC):
    """Abstract interface for long-term memory persistent storage."""

    @abstractmethod
    def add_memory(self, entry: LongTermMemoryEntry) -> LongTermMemoryEntry:
        """Persist a new memory entry."""

    @abstractmethod
    def get_memory(self, memory_id: str) -> LongTermMemoryEntry | None:
        """Fetch memory entry by memory_id."""

    @abstractmethod
    def update_memory(self, entry: LongTermMemoryEntry) -> LongTermMemoryEntry | None:
        """Update an existing memory entry."""

    @abstractmethod
    def delete_memory(self, memory_id: str, soft_delete: bool = True) -> bool:
        """Delete or deactivate a memory entry."""

    @abstractmethod
    def list_memories(
        self,
        memory_type: str | None = None,
        subject: str | None = None,
        status: str = "ACTIVE",
    ) -> list[LongTermMemoryEntry]:
        """List and filter memory entries."""

    @abstractmethod
    def find_by_type_subject(
        self, memory_type: str, subject: str, status: str = "ACTIVE"
    ) -> LongTermMemoryEntry | None:
        """Find active memory entry matching memory_type and subject."""

    @abstractmethod
    def count(self, status: str | None = "ACTIVE") -> int:
        """Return count of stored memory entries."""

    @abstractmethod
    def clear_all(self) -> int:
        """Clear all stored memory entries."""


class SQLAlchemyMemoryRepository(IMemoryRepository):
    """SQLAlchemy implementation of IMemoryRepository managing SQLite persistence."""

    def __init__(self, db_manager: MemoryDatabaseManager) -> None:
        self.db_manager = db_manager

    def _orm_to_domain(self, orm: MemoryORM) -> LongTermMemoryEntry:
        """Convert MemoryORM database model to LongTermMemoryEntry domain dataclass."""
        meta_dict = {}
        if orm.metadata_json:
            try:
                meta_dict = json.loads(orm.metadata_json)
            except Exception:  # noqa: BLE001
                meta_dict = {}

        return LongTermMemoryEntry(
            memory_id=orm.memory_id,
            memory_type=(
                MemoryType(orm.memory_type)
                if hasattr(MemoryType, orm.memory_type)
                else MemoryType.PREFERENCE
            ),
            subject=orm.subject,
            content=orm.content,
            source=(
                MemorySource(orm.source)
                if hasattr(MemorySource, orm.source)
                else MemorySource.USER_EXPLICIT
            ),
            confidence=orm.confidence,
            importance=(
                MemoryImportance(orm.importance)
                if hasattr(MemoryImportance, orm.importance)
                else MemoryImportance.MEDIUM
            ),
            user_control_state=(
                UserControlState(orm.user_control_state)
                if hasattr(UserControlState, orm.user_control_state)
                else UserControlState.ACTIVE
            ),
            sensitivity=(
                SensitivityLevel(orm.sensitivity)
                if hasattr(SensitivityLevel, orm.sensitivity)
                else SensitivityLevel.NORMAL
            ),
            session_origin=orm.session_origin,
            metadata=meta_dict,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            expires_at=orm.expires_at,
        )

    def _domain_to_orm(self, entry: LongTermMemoryEntry) -> MemoryORM:
        """Convert LongTermMemoryEntry domain dataclass to MemoryORM database model."""
        meta_str = json.dumps(entry.metadata or {})
        return MemoryORM(
            memory_id=entry.memory_id,
            memory_type=(
                entry.memory_type.value
                if isinstance(entry.memory_type, MemoryType)
                else str(entry.memory_type)
            ),
            subject=entry.subject,
            content=entry.content,
            source=(
                entry.source.value
                if isinstance(entry.source, MemorySource)
                else str(entry.source)
            ),
            confidence=entry.confidence,
            importance=(
                entry.importance.value
                if isinstance(entry.importance, MemoryImportance)
                else str(entry.importance)
            ),
            user_control_state=(
                entry.user_control_state.value
                if isinstance(entry.user_control_state, UserControlState)
                else str(entry.user_control_state)
            ),
            sensitivity=(
                entry.sensitivity.value
                if isinstance(entry.sensitivity, SensitivityLevel)
                else str(entry.sensitivity)
            ),
            session_origin=entry.session_origin,
            metadata_json=meta_str,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
            expires_at=entry.expires_at,
        )

    def add_memory(self, entry: LongTermMemoryEntry) -> LongTermMemoryEntry:
        """Persist a new long-term memory record."""
        session = self.db_manager.get_session()
        try:
            orm = self._domain_to_orm(entry)
            session.add(orm)
            session.commit()
            return self._orm_to_domain(orm)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_memory(self, memory_id: str) -> LongTermMemoryEntry | None:
        """Fetch memory entry by memory_id."""
        session = self.db_manager.get_session()
        try:
            orm = session.get(MemoryORM, memory_id)
            return self._orm_to_domain(orm) if orm else None
        finally:
            session.close()

    def update_memory(self, entry: LongTermMemoryEntry) -> LongTermMemoryEntry | None:
        """Update an existing memory entry in SQLite database."""
        session = self.db_manager.get_session()
        try:
            orm = session.get(MemoryORM, entry.memory_id)
            if not orm:
                return None

            orm.memory_type = (
                entry.memory_type.value
                if isinstance(entry.memory_type, MemoryType)
                else str(entry.memory_type)
            )
            orm.subject = entry.subject
            orm.content = entry.content
            orm.source = (
                entry.source.value
                if isinstance(entry.source, MemorySource)
                else str(entry.source)
            )
            orm.confidence = entry.confidence
            orm.importance = (
                entry.importance.value
                if isinstance(entry.importance, MemoryImportance)
                else str(entry.importance)
            )
            orm.user_control_state = (
                entry.user_control_state.value
                if isinstance(entry.user_control_state, UserControlState)
                else str(entry.user_control_state)
            )
            orm.sensitivity = (
                entry.sensitivity.value
                if isinstance(entry.sensitivity, SensitivityLevel)
                else str(entry.sensitivity)
            )
            orm.session_origin = entry.session_origin
            orm.metadata_json = json.dumps(entry.metadata or {})
            orm.updated_at = time.time()
            orm.expires_at = entry.expires_at

            session.commit()
            return self._orm_to_domain(orm)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_memory(self, memory_id: str, soft_delete: bool = True) -> bool:
        """Delete or soft-deactivate a memory entry."""
        session = self.db_manager.get_session()
        try:
            orm = session.get(MemoryORM, memory_id)
            if not orm:
                return False

            if soft_delete:
                orm.user_control_state = UserControlState.DELETED.value
                orm.updated_at = time.time()
            else:
                session.delete(orm)

            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_memories(
        self,
        memory_type: str | None = None,
        subject: str | None = None,
        status: str = "ACTIVE",
    ) -> list[LongTermMemoryEntry]:
        """Filter memory entries by type, subject, or control status."""
        session = self.db_manager.get_session()
        try:
            stmt = select(MemoryORM)
            if status:
                stmt = stmt.where(MemoryORM.user_control_state == status)
            if memory_type:
                stmt = stmt.where(MemoryORM.memory_type == memory_type)
            if subject:
                stmt = stmt.where(MemoryORM.subject == subject)

            stmt = stmt.order_by(MemoryORM.created_at.desc())
            results = session.scalars(stmt).all()
            return [self._orm_to_domain(r) for r in results]
        finally:
            session.close()

    def find_by_type_subject(
        self, memory_type: str, subject: str, status: str = "ACTIVE"
    ) -> LongTermMemoryEntry | None:
        """Find single active record matching memory_type and subject."""
        memories = self.list_memories(
            memory_type=memory_type, subject=subject, status=status
        )
        return memories[0] if memories else None

    def count(self, status: str | None = "ACTIVE") -> int:
        """Count memory entries matching optional status."""
        session = self.db_manager.get_session()
        try:
            stmt = select(func.count(MemoryORM.memory_id))
            if status:
                stmt = stmt.where(MemoryORM.user_control_state == status)
            return session.scalar(stmt) or 0
        finally:
            session.close()

    def clear_all(self) -> int:
        """Clear all stored long-term memory records."""
        session = self.db_manager.get_session()
        try:
            deleted_count = session.query(MemoryORM).delete()
            session.commit()
            return deleted_count
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
