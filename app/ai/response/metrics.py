"""Operational performance metrics for Dynamic Response Generation Engine.

Phase 4.5 - Dynamic Response Generation Engine
"""

import threading
from typing import Any

import numpy as np


class ResponseGenerationMetrics:
    """Thread-safe operational metrics collector for Response Generator."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests_total: int = 0
        self._successful_generations: int = 0
        self._failed_generations: int = 0
        self._fallback_count: int = 0
        self._streaming_requests: int = 0
        self._validation_failures: int = 0
        self._generation_latencies_ms: list[float] = []
        self._response_lengths: list[int] = []
        self._mode_distribution: dict[str, int] = {}
        self._status_distribution: dict[str, int] = {}

    def record_generation(
        self,
        duration_ms: float,
        response_len: int,
        status: str,
        mode: str,
        fallback_used: bool,
        is_streaming: bool = False,
    ) -> None:
        """Record a completed generation sample."""
        with self._lock:
            self._requests_total += 1
            self._generation_latencies_ms.append(duration_ms)
            self._response_lengths.append(response_len)
            if len(self._generation_latencies_ms) > 1000:
                self._generation_latencies_ms.pop(0)
                self._response_lengths.pop(0)

            if fallback_used:
                self._fallback_count += 1
                self._failed_generations += 1
            else:
                self._successful_generations += 1

            if is_streaming:
                self._streaming_requests += 1

            self._mode_distribution[mode] = self._mode_distribution.get(mode, 0) + 1
            self._status_distribution[status] = (
                self._status_distribution.get(status, 0) + 1
            )

    def record_validation_failure(self) -> None:
        """Record validation failure count."""
        with self._lock:
            self._validation_failures += 1

    def get_metrics_snapshot(self) -> dict[str, Any]:
        """Return thread-safe dictionary snapshot of metrics."""
        with self._lock:
            avg_lat = (
                float(np.mean(self._generation_latencies_ms))
                if self._generation_latencies_ms
                else 0.0
            )
            avg_len = (
                float(np.mean(self._response_lengths))
                if self._response_lengths
                else 0.0
            )

            return {
                "requests_total": self._requests_total,
                "successful_generations": self._successful_generations,
                "failed_generations": self._failed_generations,
                "fallback_count": self._fallback_count,
                "streaming_requests": self._streaming_requests,
                "validation_failures": self._validation_failures,
                "average_generation_latency_ms": round(avg_lat, 2),
                "average_response_chars": round(avg_len, 2),
                "mode_distribution": dict(self._mode_distribution),
                "status_distribution": dict(self._status_distribution),
            }

    def reset(self) -> None:
        """Reset all metric counters."""
        with self._lock:
            self._requests_total = 0
            self._successful_generations = 0
            self._failed_generations = 0
            self._fallback_count = 0
            self._streaming_requests = 0
            self._validation_failures = 0
            self._generation_latencies_ms.clear()
            self._response_lengths.clear()
            self._mode_distribution.clear()
            self._status_distribution.clear()
