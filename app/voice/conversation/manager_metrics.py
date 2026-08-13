"""Operational performance metrics for Conversation Manager & Short-Term Memory.

Phase 3.8 - Conversation Manager, Session Context & Short-Term Memory
"""

import threading
from typing import Any

import numpy as np


class ConversationManagerMetrics:
    """Thread-safe collector for Conversation Manager operational metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions_started: int = 0
        self._sessions_ended: int = 0
        self._sessions_timed_out: int = 0
        self._turns_processed: int = 0
        self._context_builds: int = 0
        self._context_evictions: int = 0
        self._references_resolved: int = 0
        self._references_ambiguous: int = 0
        self._references_not_found: int = 0
        self._clarifications_requested: int = 0
        self._clarifications_resolved: int = 0
        self._stale_events_ignored: int = 0
        self._sensitive_sanitizations: int = 0
        self._context_sizes_chars: list[int] = []

    def record_session_start(self) -> None:
        """Record session initialization."""
        with self._lock:
            self._sessions_started += 1

    def record_session_end(self, reason: str) -> None:
        """Record session termination."""
        with self._lock:
            if reason == "session_timeout":
                self._sessions_timed_out += 1
            else:
                self._sessions_ended += 1

    def record_turn(self) -> None:
        """Record processed turn."""
        with self._lock:
            self._turns_processed += 1

    def record_context_build(self, size_chars: int) -> None:
        """Record snapshot build and size."""
        with self._lock:
            self._context_builds += 1
            self._context_sizes_chars.append(size_chars)
            if len(self._context_sizes_chars) > 1000:
                self._context_sizes_chars.pop(0)

    def record_context_eviction(self) -> None:
        """Record context turn eviction."""
        with self._lock:
            self._context_evictions += 1

    def record_reference_resolution(self, status_str: str) -> None:
        """Record reference resolution result."""
        with self._lock:
            if status_str == "RESOLVED":
                self._references_resolved += 1
            elif status_str == "AMBIGUOUS":
                self._references_ambiguous += 1
            elif status_str == "NOT_FOUND":
                self._references_not_found += 1

    def record_clarification(self, resolved: bool = False) -> None:
        """Record clarification request or resolution."""
        with self._lock:
            if resolved:
                self._clarifications_resolved += 1
            else:
                self._clarifications_requested += 1

    def record_sensitive_sanitization(self) -> None:
        """Record sensitive data masking action."""
        with self._lock:
            self._sensitive_sanitizations += 1

    def get_metrics_snapshot(self) -> dict[str, Any]:
        """Return thread-safe dictionary snapshot of metrics."""
        with self._lock:
            avg_size = (
                float(np.mean(self._context_sizes_chars))
                if self._context_sizes_chars
                else 0.0
            )
            return {
                "sessions_started": self._sessions_started,
                "sessions_ended": self._sessions_ended,
                "sessions_timed_out": self._sessions_timed_out,
                "turns_processed": self._turns_processed,
                "context_builds": self._context_builds,
                "context_evictions": self._context_evictions,
                "references_resolved": self._references_resolved,
                "references_ambiguous": self._references_ambiguous,
                "references_not_found": self._references_not_found,
                "clarifications_requested": self._clarifications_requested,
                "clarifications_resolved": self._clarifications_resolved,
                "stale_events_ignored": self._stale_events_ignored,
                "sensitive_sanitizations": self._sensitive_sanitizations,
                "average_context_size_chars": round(avg_size, 1),
            }

    def reset(self) -> None:
        """Reset counters."""
        with self._lock:
            self._sessions_started = 0
            self._sessions_ended = 0
            self._sessions_timed_out = 0
            self._turns_processed = 0
            self._context_builds = 0
            self._context_evictions = 0
            self._references_resolved = 0
            self._references_ambiguous = 0
            self._references_not_found = 0
            self._clarifications_requested = 0
            self._clarifications_resolved = 0
            self._stale_events_ignored = 0
            self._sensitive_sanitizations = 0
            self._context_sizes_chars.clear()
