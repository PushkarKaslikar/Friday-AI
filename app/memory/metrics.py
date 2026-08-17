"""Metrics tracking for Phase 5.1 Short-Term Memory Subsystem.

Phase 5.1 - Short-Term Memory Foundation & Active Conversation Memory
"""

import threading
from typing import Any


class MemoryMetrics:
    """Thread-safe collector for memory operation performance and event metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.entries_added: int = 0
        self.entries_updated: int = 0
        self.entries_evicted: int = 0
        self.entries_invalidated: int = 0
        self.snapshots_created: int = 0
        self.total_snapshot_latency_ms: float = 0.0
        self.retrieval_count: int = 0
        self.session_resets: int = 0
        self.memory_errors: int = 0

    def record_entry_added(self) -> None:
        """Record addition of a new memory entry."""
        with self._lock:
            self.entries_added += 1

    def record_entry_updated(self) -> None:
        """Record update of an existing memory entry."""
        with self._lock:
            self.entries_updated += 1

    def record_entry_evicted(self, count: int = 1) -> None:
        """Record eviction of memory entries."""
        with self._lock:
            self.entries_evicted += count

    def record_entry_invalidated(self) -> None:
        """Record invalidation of an entity/entry."""
        with self._lock:
            self.entries_invalidated += 1

    def record_snapshot(self, latency_ms: float) -> None:
        """Record creation of a memory snapshot."""
        with self._lock:
            self.snapshots_created += 1
            self.total_snapshot_latency_ms += latency_ms

    def record_retrieval(self) -> None:
        """Record a memory query/retrieval call."""
        with self._lock:
            self.retrieval_count += 1

    def record_session_reset(self) -> None:
        """Record a session memory reset."""
        with self._lock:
            self.session_resets += 1

    def record_error(self) -> None:
        """Record a memory subsystem error."""
        with self._lock:
            self.memory_errors += 1

    def get_metrics_summary(self) -> dict[str, Any]:
        """Return a snapshot dictionary of aggregated metrics."""
        with self._lock:
            avg_snapshot_latency = (
                self.total_snapshot_latency_ms / self.snapshots_created
                if self.snapshots_created > 0
                else 0.0
            )
            return {
                "entries_added": self.entries_added,
                "entries_updated": self.entries_updated,
                "entries_evicted": self.entries_evicted,
                "entries_invalidated": self.entries_invalidated,
                "snapshots_created": self.snapshots_created,
                "average_snapshot_latency_ms": round(avg_snapshot_latency, 3),
                "retrieval_count": self.retrieval_count,
                "session_resets": self.session_resets,
                "memory_errors": self.memory_errors,
            }
