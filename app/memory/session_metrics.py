"""Metrics collector for Phase 5.2 Session Memory Subsystem.

Phase 5.2 - Session Memory & Active Session Context Management
"""

import threading
from typing import Any


class SessionMemoryMetrics:
    """Thread-safe collector for session memory metrics and event counters."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.sessions_created: int = 0
        self.sessions_ended: int = 0
        self.sessions_expired: int = 0
        self.task_count: int = 0
        self.topic_changes: int = 0
        self.workflow_count: int = 0
        self.workflow_failures: int = 0
        self.clarifications: int = 0
        self.corrections: int = 0
        self.retries: int = 0
        self.entity_updates: int = 0
        self.snapshot_count: int = 0
        self.total_snapshot_latency_ms: float = 0.0
        self.stale_update_rejections: int = 0
        self.memory_evictions: int = 0

    def record_session_created(self) -> None:
        """Record session context creation."""
        with self._lock:
            self.sessions_created += 1

    def record_session_ended(self) -> None:
        """Record session context completion."""
        with self._lock:
            self.sessions_ended += 1

    def record_task_created(self) -> None:
        """Record session task initialization."""
        with self._lock:
            self.task_count += 1

    def record_topic_changed(self) -> None:
        """Record session topic transition."""
        with self._lock:
            self.topic_changes += 1

    def record_workflow(self, success: bool = True) -> None:
        """Record workflow execution."""
        with self._lock:
            self.workflow_count += 1
            if not success:
                self.workflow_failures += 1

    def record_clarification(self) -> None:
        """Record pending clarification event."""
        with self._lock:
            self.clarifications += 1

    def record_correction(self) -> None:
        """Record user correction event."""
        with self._lock:
            self.corrections += 1

    def record_snapshot(self, latency_ms: float) -> None:
        """Record session snapshot creation."""
        with self._lock:
            self.snapshot_count += 1
            self.total_snapshot_latency_ms += latency_ms

    def record_stale_rejection(self) -> None:
        """Record stale update rejection."""
        with self._lock:
            self.stale_update_rejections += 1

    def get_metrics_summary(self) -> dict[str, Any]:
        """Return aggregated session metrics dictionary."""
        with self._lock:
            avg_snap_latency = (
                self.total_snapshot_latency_ms / self.snapshot_count
                if self.snapshot_count > 0
                else 0.0
            )
            return {
                "sessions_created": self.sessions_created,
                "sessions_ended": self.sessions_ended,
                "sessions_expired": self.sessions_expired,
                "task_count": self.task_count,
                "topic_changes": self.topic_changes,
                "workflow_count": self.workflow_count,
                "workflow_failures": self.workflow_failures,
                "clarifications": self.clarifications,
                "corrections": self.corrections,
                "retries": self.retries,
                "entity_updates": self.entity_updates,
                "snapshot_count": self.snapshot_count,
                "average_snapshot_latency_ms": round(avg_snap_latency, 3),
                "stale_update_rejections": self.stale_update_rejections,
                "memory_evictions": self.memory_evictions,
            }
