"""Telemetry metrics tracker for UI Automation operations."""

import threading
from typing import Any


class UIAutomationMetrics:
    """Thread-safe performance and operational counter metrics tracker."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.engine_initializations: int = 0
        self.window_enumerations: int = 0
        self.element_searches: int = 0
        self.search_successes: int = 0
        self.search_ambiguities: int = 0
        self.tree_traversals: int = 0
        self.tree_truncations: int = 0
        self.pattern_detections: int = 0
        self.stale_element_errors: int = 0
        self.process_exit_errors: int = 0

        self._lookup_latencies: list[float] = []
        self._traversal_latencies: list[float] = []

    def record_engine_init(self) -> None:
        with self._lock:
            self.engine_initializations += 1

    def record_window_enum(self) -> None:
        with self._lock:
            self.window_enumerations += 1

    def record_element_search(
        self, success: bool = True, ambiguous: bool = False, latency_ms: float = 0.0
    ) -> None:
        with self._lock:
            self.element_searches += 1
            if success:
                self.search_successes += 1
            if ambiguous:
                self.search_ambiguities += 1
            if latency_ms > 0:
                self._lookup_latencies.append(latency_ms)
                if len(self._lookup_latencies) > 1000:
                    self._lookup_latencies.pop(0)

    def record_tree_traversal(
        self, truncated: bool = False, latency_ms: float = 0.0
    ) -> None:
        with self._lock:
            self.tree_traversals += 1
            if truncated:
                self.tree_truncations += 1
            if latency_ms > 0:
                self._traversal_latencies.append(latency_ms)
                if len(self._traversal_latencies) > 1000:
                    self._traversal_latencies.pop(0)

    def record_pattern_detection(self) -> None:
        with self._lock:
            self.pattern_detections += 1

    def record_stale_element_error(self) -> None:
        with self._lock:
            self.stale_element_errors += 1

    def record_process_exit_error(self) -> None:
        with self._lock:
            self.process_exit_errors += 1

    def get_metrics_summary(self) -> dict[str, Any]:
        """Return aggregated snapshot of metrics."""
        with self._lock:
            avg_lookup_ms = (
                sum(self._lookup_latencies) / len(self._lookup_latencies)
                if self._lookup_latencies
                else 0.0
            )
            avg_traversal_ms = (
                sum(self._traversal_latencies) / len(self._traversal_latencies)
                if self._traversal_latencies
                else 0.0
            )
            return {
                "engine_initializations": self.engine_initializations,
                "window_enumerations": self.window_enumerations,
                "element_searches": self.element_searches,
                "search_successes": self.search_successes,
                "search_ambiguities": self.search_ambiguities,
                "tree_traversals": self.tree_traversals,
                "tree_truncations": self.tree_truncations,
                "pattern_detections": self.pattern_detections,
                "stale_element_errors": self.stale_element_errors,
                "process_exit_errors": self.process_exit_errors,
                "avg_lookup_latency_ms": round(avg_lookup_ms, 2),
                "avg_traversal_latency_ms": round(avg_traversal_ms, 2),
            }
