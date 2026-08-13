"""Operational performance metrics for Local LLM Runtime.

Phase 4.1 - Local LLM Runtime & Model Provider Foundation
"""

import threading
from typing import Any

import numpy as np


class LLMMetrics:
    """Thread-safe collector for Local LLM operational metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model_load_count: int = 0
        self._generation_count: int = 0
        self._successful_generations: int = 0
        self._failed_generations: int = 0
        self._tokens_generated: int = 0
        self._load_durations_ms: list[float] = []
        self._generation_latencies_ms: list[float] = []
        self._tokens_per_second_list: list[float] = []

    def record_model_load(self, duration_ms: float) -> None:
        """Record model load duration."""
        with self._lock:
            self._model_load_count += 1
            self._load_durations_ms.append(duration_ms)
            if len(self._load_durations_ms) > 100:
                self._load_durations_ms.pop(0)

    def record_generation(
        self,
        duration_ms: float,
        tokens_count: int,
        tokens_per_second: float,
        success: bool = True,
    ) -> None:
        """Record inference generation metrics."""
        with self._lock:
            self._generation_count += 1
            if success:
                self._successful_generations += 1
                self._tokens_generated += tokens_count
                self._generation_latencies_ms.append(duration_ms)
                if tokens_per_second > 0:
                    self._tokens_per_second_list.append(tokens_per_second)
                if len(self._generation_latencies_ms) > 1000:
                    self._generation_latencies_ms.pop(0)
                    self._tokens_per_second_list.pop(0)
            else:
                self._failed_generations += 1

    def get_metrics_snapshot(self) -> dict[str, Any]:
        """Return thread-safe dictionary snapshot of metrics."""
        with self._lock:
            avg_load = (
                float(np.mean(self._load_durations_ms))
                if self._load_durations_ms
                else 0.0
            )
            avg_latency = (
                float(np.mean(self._generation_latencies_ms))
                if self._generation_latencies_ms
                else 0.0
            )
            avg_tps = (
                float(np.mean(self._tokens_per_second_list))
                if self._tokens_per_second_list
                else 0.0
            )

            return {
                "model_load_count": self._model_load_count,
                "average_load_duration_ms": round(avg_load, 2),
                "generation_count": self._generation_count,
                "successful_generations": self._successful_generations,
                "failed_generations": self._failed_generations,
                "tokens_generated": self._tokens_generated,
                "average_generation_latency_ms": round(avg_latency, 2),
                "average_tokens_per_second": round(avg_tps, 2),
            }

    def reset(self) -> None:
        """Reset all metric counters."""
        with self._lock:
            self._model_load_count = 0
            self._generation_count = 0
            self._successful_generations = 0
            self._failed_generations = 0
            self._tokens_generated = 0
            self._load_durations_ms.clear()
            self._generation_latencies_ms.clear()
            self._tokens_per_second_list.clear()
