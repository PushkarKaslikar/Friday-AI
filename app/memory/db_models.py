"""SQLAlchemy ORM models for Phase 5.3 Long-Term Memory SQLite database.

Phase 5.3 - Long-Term Memory & Persistent Memory Foundation
"""

import time

from sqlalchemy import Float, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for Friday SQLAlchemy ORM models."""


class MemoryORM(Base):
    """ORM database table storing persistent long-term memory entries."""

    __tablename__ = "friday_long_term_memories"

    memory_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    memory_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(
        String(64), nullable=False, default="USER_EXPLICIT"
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    importance: Mapped[str] = mapped_column(
        String(32), nullable=False, default="MEDIUM"
    )
    user_control_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ACTIVE", index=True
    )
    sensitivity: Mapped[str] = mapped_column(
        String(32), nullable=False, default="NORMAL"
    )
    session_origin: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False)
    expires_at: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index(
            "idx_type_subject_status", "memory_type", "subject", "user_control_state"
        ),
    )


class SemanticIndexEntryORM(Base):
    """ORM model mapping FAISS vector IDs to SQLite memory IDs and content hashes."""

    __tablename__ = "friday_semantic_index_entries"

    faiss_vector_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    memory_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    embedding_model: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    index_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="INDEXED", index=True
    )
    created_at: Mapped[float] = mapped_column(Float, nullable=False, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False, default=time.time)

    __table_args__ = (Index("idx_semantic_memory_status", "memory_id", "status"),)


class SchemaVersionORM(Base):
    """ORM database table tracking SQLite schema migrations and versions."""

    __tablename__ = "friday_schema_versions"

    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    applied_at: Mapped[float] = mapped_column(Float, nullable=False, default=time.time)
