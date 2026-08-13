"""Operational performance metrics for Personality Engine.

Phase 4.4 - Personality Engine & Behavioral Identity System
"""

import threading
from typing import Any

import numpy as np


class PersonalityMetrics:
    """Thread-safe operational metrics collector for Personality Engine."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._context_generations: int = 0
        self._modifier_applications: int = 0
        self._generation_latencies_ms: list[float] = []
        self._snippet_lengths: list[int] = []
        self._emotional_signal_counts: dict[str, int] = {}
        self._style_mode_counts: dict[str, int] = {}

    def record_context_generation(
        self,
        duration_ms: float,
        snippet_len: int,
        emotional_signal: str,
        style_mode: str,
    ) -> None:
        """Record context generation metric sample."""
        with self._lock:
            self._context_generations += 1
            self._generation_latencies_ms.append(duration_ms)
            self._snippet_lengths.append(snippet_len)
            if len(self._generation_latencies_ms) > 1000:
                self._generation_latencies_ms.pop(0)
                self._snippet_lengths.pop(0)

            self._emotional_signal_counts[emotional_signal] = (
                self._emotional_signal_counts.get(emotional_signal, 0) + 1
            )
            self._style_mode_counts[style_mode] = (
                self._style_mode_counts.get(style_mode, 0) + 1
            )

    def record_modifier_applied(self) -> None:
        """Record modifier application count."""
        with self._lock:
            self._modifier_applications += 1

    def get_metrics_snapshot(self) -> dict[str, Any]:
        """Return thread-safe dictionary snapshot of metrics."""
        with self._lock:
            avg_lat = (
                float(np.mean(self._generation_latencies_ms))
                if self._generation_latencies_ms
                else 0.0
            )
            avg_len = (
                float(np.mean(self._snippet_lengths)) if self._snippet_lengths else 0.0
            )

            return {
                "context_generations": self._context_generations,
                "modifier_applications": self._modifier_applications,
                "average_generation_latency_ms": round(avg_lat, 2),
                "average_snippet_length_chars": round(avg_len, 2),
                "emotional_signal_counts": dict(self._emotional_signal_counts),
                "style_mode_counts": dict(self._style_mode_counts),
            }

    def reset(self) -> None:
        """Reset all metric counters."""
        with self._lock:
            self._context_generations = 0
            self._modifier_applications = 0
            self._generation_latencies_ms.clear()
            self._snippet_lengths.clear()
            self._emotional_signal_counts.clear()
            self._style_mode_counts.clear()
