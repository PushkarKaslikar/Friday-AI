"""Thread-safe telemetry metrics for Phase 6.3 desktop subsystem."""

import threading
from typing import Any


class DesktopMetrics:
    """Tracks non-sensitive operation counts, latencies, and status metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.total_operations: int = 0
        self.completed_operations: int = 0
        self.failed_operations: int = 0
        self.window_queries: int = 0
        self.active_window_queries: int = 0
        self.window_focuses: int = 0
        self.window_moves: int = 0
        self.window_resizes: int = 0
        self.window_snaps: int = 0
        self.workspace_captures: int = 0
        self.workspace_restores: int = 0
        self.screen_captures: int = 0
        self.clipboard_reads: int = 0
        self.clipboard_writes: int = 0
        self.total_latency_ms: float = 0.0

    def record_operation(
        self, op_type: str, status_str: str, duration_ms: float
    ) -> None:
        """Record completed desktop operation metrics."""
        with self._lock:
            self.total_operations += 1
            self.total_latency_ms += max(0.0, duration_ms)

            if status_str in ("COMPLETED", "SUCCESS", "RESTORED"):
                self.completed_operations += 1
            else:
                self.failed_operations += 1

            if "list_windows" in op_type or "get_window" in op_type:
                self.window_queries += 1
            elif "active_window" in op_type:
                self.active_window_queries += 1
            elif "focus" in op_type:
                self.window_focuses += 1
            elif "move" in op_type:
                self.window_moves += 1
            elif "resize" in op_type:
                self.window_resizes += 1
            elif "snap" in op_type:
                self.window_snaps += 1
            elif "workspace_capture" in op_type:
                self.workspace_captures += 1
            elif "workspace_restore" in op_type:
                self.workspace_restores += 1
            elif "screen_capture" in op_type or "capture_" in op_type:
                self.screen_captures += 1
            elif "clipboard_read" in op_type or "get_text" in op_type:
                self.clipboard_reads += 1
            elif "clipboard_write" in op_type or "set_text" in op_type:
                self.clipboard_writes += 1

    def to_dict(self) -> dict[str, Any]:
        """Return snapshot dictionary of metrics."""
        with self._lock:
            avg_lat = (
                self.total_latency_ms / self.total_operations
                if self.total_operations > 0
                else 0.0
            )
            return {
                "total_operations": self.total_operations,
                "completed_operations": self.completed_operations,
                "failed_operations": self.failed_operations,
                "window_queries": self.window_queries,
                "active_window_queries": self.active_window_queries,
                "window_focuses": self.window_focuses,
                "window_moves": self.window_moves,
                "window_resizes": self.window_resizes,
                "window_snaps": self.window_snaps,
                "workspace_captures": self.workspace_captures,
                "workspace_restores": self.workspace_restores,
                "screen_captures": self.screen_captures,
                "clipboard_reads": self.clipboard_reads,
                "clipboard_writes": self.clipboard_writes,
                "average_latency_ms": round(avg_lat, 2),
            }

    def reset(self) -> None:
        """Reset all metric counters."""
        with self._lock:
            self.total_operations = 0
            self.completed_operations = 0
            self.failed_operations = 0
            self.window_queries = 0
            self.active_window_queries = 0
            self.window_focuses = 0
            self.window_moves = 0
            self.window_resizes = 0
            self.window_snaps = 0
            self.workspace_captures = 0
            self.workspace_restores = 0
            self.screen_captures = 0
            self.clipboard_reads = 0
            self.clipboard_writes = 0
            self.total_latency_ms = 0.0
