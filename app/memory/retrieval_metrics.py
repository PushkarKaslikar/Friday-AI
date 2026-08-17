"""Thread-safe operational telemetry and metrics for Memory Retrieval Subsystem.

Phase 5.6 - Memory Retrieval & Relevant Context Engine
"""

import threading


class MemoryRetrievalMetrics:
    """Thread-safe telemetry collector for Phase 5.6 Memory Retrieval."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests = 0
        self._triggered = 0
        self._skipped = 0
        self._semantic_searches = 0
        self._structured_searches = 0
        self._candidates_found = 0
        self._candidates_filtered = 0
        self._memories_selected = 0
        self._no_result_count = 0
        self._degraded_count = 0
        self._failure_count = 0
        self._total_latency_ms = 0.0
        self._last_latency_ms = 0.0
        self._total_context_chars = 0

    def record_request(
        self,
        triggered: bool,
        skipped: bool,
        mode: str,
        latency_ms: float,
        candidates_found: int,
        candidates_filtered: int,
        selected_count: int,
        context_chars: int,
        degraded: bool = False,
        failed: bool = False,
    ) -> None:
        """Record telemetry for a single retrieval turn."""
        with self._lock:
            self._requests += 1
            if triggered:
                self._triggered += 1
            if skipped:
                self._skipped += 1
            if degraded:
                self._degraded_count += 1
            if failed:
                self._failure_count += 1

            self._candidates_found += candidates_found
            self._candidates_filtered += candidates_filtered
            self._memories_selected += selected_count
            if triggered and selected_count == 0:
                self._no_result_count += 1

            self._total_latency_ms += latency_ms
            self._last_latency_ms = latency_ms
            self._total_context_chars += context_chars

    def record_search(self, is_semantic: bool) -> None:
        """Record execution of semantic vs. structured search."""
        with self._lock:
            if is_semantic:
                self._semantic_searches += 1
            else:
                self._structured_searches += 1

    def snapshot(self) -> dict:
        """Return a thread-safe snapshot of retrieval telemetry."""
        with self._lock:
            avg_lat = (
                self._total_latency_ms / self._requests if self._requests > 0 else 0.0
            )
            return {
                "retrieval_requests": self._requests,
                "retrieval_triggered": self._triggered,
                "retrieval_skipped": self._skipped,
                "semantic_searches": self._semantic_searches,
                "structured_searches": self._structured_searches,
                "candidates_found": self._candidates_found,
                "candidates_filtered": self._candidates_filtered,
                "memories_selected": self._memories_selected,
                "no_result_count": self._no_result_count,
                "degraded_count": self._degraded_count,
                "failure_count": self._failure_count,
                "average_latency_ms": round(avg_lat, 2),
                "last_latency_ms": round(self._last_latency_ms, 2),
                "total_context_chars": self._total_context_chars,
            }
