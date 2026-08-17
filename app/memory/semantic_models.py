"""Semantic Memory & Local Vector Index domain models and enums.

Phase 5.5 - Semantic Memory & Local Vector Index Foundation
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class EmbeddingStatus(str, Enum):
    """Lifecycle status for local embedding model provider."""

    UNINITIALIZED = "UNINITIALIZED"
    LOADING = "LOADING"
    READY = "READY"
    EMBEDDING = "EMBEDDING"
    UNLOADED = "UNLOADED"
    ERROR = "ERROR"


class IndexSyncStatus(str, Enum):
    """Synchronization status of local FAISS vector index relative to SQLite."""

    SYNCED = "SYNCED"
    SYNCING = "SYNCING"
    OUT_OF_SYNC = "OUT_OF_SYNC"
    REBUILD_REQUIRED = "REBUILD_REQUIRED"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


@dataclass
class EmbeddingRequest:
    """Structured request for generating vector embeddings."""

    text: str
    memory_id: str = ""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)


@dataclass
class EmbeddingResult:
    """Structured result of a vector embedding generation."""

    request_id: str
    text: str
    vector: list[float]
    dimension: int
    norm: float = 1.0
    duration_ms: float = 0.0
    status: str = "SUCCESS"
    error_message: str = ""


@dataclass
class SemanticSearchResult:
    """Low-level result returned from semantic vector index search primitive."""

    memory_id: str
    vector_id: int
    similarity: float
    distance: float = 0.0
    embedding_model: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class ConsistencyReport:
    """Diagnostic consistency report between SQLite persistent storage and FAISS vector index."""

    is_consistent: bool = True
    vector_count: int = 0
    sqlite_memory_count: int = 0
    orphan_vector_ids: list[int] = field(default_factory=list)
    missing_memory_ids: list[str] = field(default_factory=list)
    stale_hash_count: int = 0
    dimension_mismatch: bool = False
    model_mismatch: bool = False
    errors: list[str] = field(default_factory=list)
    checked_at: float = field(default_factory=time.time)


@dataclass
class SemanticMemoryConfig:
    """Configuration settings for Phase 5.5 Semantic Memory subsystem."""

    enabled: bool = True
    embedding_provider: str = "local"
    embedding_model: str = "all-MiniLM-L6-v2"
    device: str = "AUTO"
    batch_size: int = 32
    normalize_embeddings: bool = True
    top_k: int = 10
    index_path: str = ""
    index_version: int = 1
    auto_sync: bool = True
    max_memory_text_chars: int = 1000
