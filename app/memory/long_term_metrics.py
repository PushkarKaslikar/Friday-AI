"""Metrics collector for Phase 5.3 Long-Term Persistent Memory.

Phase 5.3 - Long-Term Memory & Persistent Memory Foundation
"""

import threading
from typing import Any


class LongTermMemoryMetrics:
    """Thread-safe metrics collector for Long-Term Memory persistence and promotion statistics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.memory_writes: int = 0
        self.memory_updates: int = 0
        self.memory_deletes: int = 0
        self.memory_reads: int = 0
        self.promotion_attempts: int = 0
        self.promotion_successes: int = 0
        self.promotion_rejections: int = 0
        self.deduplication_events: int = 0
        self.conflict_resolutions: int = 0
        self.db_errors: int = 0
        self.total_query_latency_ms: float = 0.0

    def record_write(self) -> None:
        """Record a new persistent memory write."""
        with self._lock:
            self.memory_writes += 1

    def record_update(self) -> None:
        """Record a persistent memory update."""
        with self._lock:
            self.memory_updates += 1

    def record_delete(self) -> None:
        """Record a memory deletion event."""
        with self._lock:
            self.memory_deletes += 1

    def record_read(self) -> None:
        """Record a memory read operation."""
        with self._lock:
            self.memory_reads += 1

    def record_promotion(
        self, success: bool, is_dedup: bool = False, is_conflict: bool = False
    ) -> None:
        """Record a candidate promotion event."""
        with self._lock:
            self.promotion_attempts += 1
            if success:
                self.promotion_successes += 1
                if is_dedup:
                    self.deduplication_events += 1
                if is_conflict:
                    self.conflict_resolutions += 1
            else:
                self.promotion_rejections += 1

    def record_db_error(self) -> None:
        """Record a database failure or exception."""
        with self._lock:
            self.db_errors += 1

    def get_metrics_summary(self) -> dict[str, Any]:
        """Return aggregated long-term memory metrics dictionary."""
        with self._lock:
            return {
                "memory_writes": self.memory_writes,
                "memory_updates": self.memory_updates,
                "memory_deletes": self.memory_deletes,
                "memory_reads": self.memory_reads,
                "promotion_attempts": self.promotion_attempts,
                "promotion_successes": self.promotion_successes,
                "promotion_rejections": self.promotion_rejections,
                "deduplication_events": self.deduplication_events,
                "conflict_resolutions": self.conflict_resolutions,
                "db_errors": self.db_errors,
            }
