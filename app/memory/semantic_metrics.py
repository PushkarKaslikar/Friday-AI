"""Metrics tracker for Phase 5.5 Semantic Memory subsystem.

Phase 5.5 - Semantic Memory & Local Vector Index Foundation
"""

import threading


class SemanticMemoryMetrics:
    """Thread-safe metrics tracker for semantic memory embedding and vector indexing operations."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._embedding_requests = 0
        self._embedding_failures = 0
        self._total_embedded_texts = 0
        self._indexed_memories = 0
        self._updated_vectors = 0
        self._removed_vectors = 0
        self._rebuild_count = 0
        self._rebuild_failures = 0
        self._sync_runs = 0
        self._sync_failures = 0
        self._index_searches = 0
        self._search_failures = 0
        self._consistency_failures = 0
        self._last_embedding_duration_ms = 0.0
        self._last_search_duration_ms = 0.0

    def record_embedding_request(
        self, count: int = 1, duration_ms: float = 0.0
    ) -> None:
        with self._lock:
            self._embedding_requests += 1
            self._total_embedded_texts += count
            self._last_embedding_duration_ms = duration_ms

    def record_embedding_failure(self) -> None:
        with self._lock:
            self._embedding_failures += 1

    def record_indexed_memory(self, count: int = 1) -> None:
        with self._lock:
            self._indexed_memories += count

    def record_updated_vector(self, count: int = 1) -> None:
        with self._lock:
            self._updated_vectors += count

    def record_removed_vector(self, count: int = 1) -> None:
        with self._lock:
            self._removed_vectors += count

    def record_rebuild(self, success: bool = True) -> None:
        with self._lock:
            self._rebuild_count += 1
            if not success:
                self._rebuild_failures += 1

    def record_sync(self, success: bool = True) -> None:
        with self._lock:
            self._sync_runs += 1
            if not success:
                self._sync_failures += 1

    def record_search(self, duration_ms: float = 0.0, success: bool = True) -> None:
        with self._lock:
            self._index_searches += 1
            self._last_search_duration_ms = duration_ms
            if not success:
                self._search_failures += 1

    def record_consistency_failure(self) -> None:
        with self._lock:
            self._consistency_failures += 1

    def get_metrics_summary(self) -> dict:
        with self._lock:
            return {
                "embedding_requests": self._embedding_requests,
                "embedding_failures": self._embedding_failures,
                "total_embedded_texts": self._total_embedded_texts,
                "indexed_memories": self._indexed_memories,
                "updated_vectors": self._updated_vectors,
                "removed_vectors": self._removed_vectors,
                "rebuild_count": self._rebuild_count,
                "rebuild_failures": self._rebuild_failures,
                "sync_runs": self._sync_runs,
                "sync_failures": self._sync_failures,
                "index_searches": self._index_searches,
                "search_failures": self._search_failures,
                "consistency_failures": self._consistency_failures,
                "last_embedding_duration_ms": round(
                    self._last_embedding_duration_ms, 2
                ),
                "last_search_duration_ms": round(self._last_search_duration_ms, 2),
            }
