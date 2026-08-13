"""Operational performance metrics for Natural Greetings Subsystem.

Phase 3.9 - Natural Greetings Foundation & Context-Aware Activation Responses
"""

import threading
from typing import Any

import numpy as np


class GreetingMetrics:
    """Thread-safe collector for Natural Greetings operational metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._greetings_generated: int = 0
        self._greetings_spoken: int = 0
        self._greetings_skipped: int = 0
        self._greeting_failures: int = 0
        self._repeated_preventions: int = 0
        self._fallbacks_used: int = 0
        self._generation_latencies_ms: list[float] = []

    def record_generation(self, latency_ms: float = 0.0) -> None:
        """Record greeting generation."""
        with self._lock:
            self._greetings_generated += 1
            self._generation_latencies_ms.append(latency_ms)
            if len(self._generation_latencies_ms) > 1000:
                self._generation_latencies_ms.pop(0)

    def record_spoken(self) -> None:
        """Record spoken greeting."""
        with self._lock:
            self._greetings_spoken += 1

    def record_skipped(self) -> None:
        """Record skipped greeting."""
        with self._lock:
            self._greetings_skipped += 1

    def record_failure(self, fallback_used: bool = True) -> None:
        """Record greeting generation failure."""
        with self._lock:
            self._greeting_failures += 1
            if fallback_used:
                self._fallbacks_used += 1

    def record_repetition_prevention(self) -> None:
        """Record repetition prevention filter action."""
        with self._lock:
            self._repeated_preventions += 1

    def get_metrics_snapshot(self) -> dict[str, Any]:
        """Return thread-safe snapshot of collected metrics."""
        with self._lock:
            avg_latency = (
                float(np.mean(self._generation_latencies_ms))
                if self._generation_latencies_ms
                else 0.0
            )
            return {
                "greetings_generated": self._greetings_generated,
                "greetings_spoken": self._greetings_spoken,
                "greetings_skipped": self._greetings_skipped,
                "greeting_failures": self._greeting_failures,
                "repeated_preventions": self._repeated_preventions,
                "fallbacks_used": self._fallbacks_used,
                "average_generation_latency_ms": round(avg_latency, 2),
            }

    def reset(self) -> None:
        """Reset counters."""
        with self._lock:
            self._greetings_generated = 0
            self._greetings_spoken = 0
            self._greetings_skipped = 0
            self._greeting_failures = 0
            self._repeated_preventions = 0
            self._fallbacks_used = 0
            self._generation_latencies_ms.clear()
