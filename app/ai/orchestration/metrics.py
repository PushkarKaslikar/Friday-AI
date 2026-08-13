"""Operational performance metrics for AI Orchestrator.

Phase 4.2 - AI Orchestrator & Reasoning Workflow Engine
"""

import threading
from typing import Any

import numpy as np


class OrchestratorMetrics:
    """Thread-safe operational metrics collector for AI Orchestrator."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total_requests: int = 0
        self._successful_orchestrations: int = 0
        self._failed_orchestrations: int = 0
        self._total_tool_calls: int = 0
        self._plans_created: int = 0
        self._durations_ms: list[float] = []

    def record_request(
        self,
        duration_ms: float,
        tool_calls_count: int,
        success: bool = True,
        plan_created: bool = False,
    ) -> None:
        """Record an orchestration request outcome."""
        with self._lock:
            self._total_requests += 1
            if success:
                self._successful_orchestrations += 1
                self._durations_ms.append(duration_ms)
                if len(self._durations_ms) > 1000:
                    self._durations_ms.pop(0)
            else:
                self._failed_orchestrations += 1

            self._total_tool_calls += tool_calls_count
            if plan_created:
                self._plans_created += 1

    def get_metrics_snapshot(self) -> dict[str, Any]:
        """Return thread-safe dictionary snapshot of metrics."""
        with self._lock:
            avg_dur = float(np.mean(self._durations_ms)) if self._durations_ms else 0.0

            return {
                "total_requests": self._total_requests,
                "successful_orchestrations": self._successful_orchestrations,
                "failed_orchestrations": self._failed_orchestrations,
                "total_tool_calls": self._total_tool_calls,
                "plans_created": self._plans_created,
                "average_duration_ms": round(avg_dur, 2),
            }

    def reset(self) -> None:
        """Reset all metric counters."""
        with self._lock:
            self._total_requests = 0
            self._successful_orchestrations = 0
            self._failed_orchestrations = 0
            self._total_tool_calls = 0
            self._plans_created = 0
            self._durations_ms.clear()
