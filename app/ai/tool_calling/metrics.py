"""Operational performance metrics for Tool Calling Engine.

Phase 4.3 - Tool Calling & Function Binding Engine
"""

import threading
from typing import Any

import numpy as np


class ToolCallingMetrics:
    """Thread-safe operational metrics collector for Tool Calling Engine."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._calls_generated: int = 0
        self._calls_accepted: int = 0
        self._calls_rejected: int = 0
        self._unknown_tool_calls: int = 0
        self._invalid_argument_calls: int = 0
        self._authorization_required_calls: int = 0
        self._authorization_denied_calls: int = 0
        self._successful_executions: int = 0
        self._failed_executions: int = 0
        self._schema_cache_hits: int = 0
        self._schema_cache_misses: int = 0
        self._processing_durations_ms: list[float] = []

    def record_call_generated(self) -> None:
        """Record generated tool call count."""
        with self._lock:
            self._calls_generated += 1

    def record_validation_result(self, is_valid: bool, status_val: str) -> None:
        """Record validation outcome."""
        with self._lock:
            if is_valid:
                self._calls_accepted += 1
            else:
                self._calls_rejected += 1
                if status_val == "UNKNOWN_TOOL":
                    self._unknown_tool_calls += 1
                elif status_val == "INVALID_ARGUMENTS":
                    self._invalid_argument_calls += 1

    def record_execution_result(self, status_val: str, duration_ms: float) -> None:
        """Record execution outcome and duration."""
        with self._lock:
            self._processing_durations_ms.append(duration_ms)
            if len(self._processing_durations_ms) > 1000:
                self._processing_durations_ms.pop(0)

            if status_val == "SUCCESS":
                self._successful_executions += 1
            elif status_val == "AUTHORIZATION_REQUIRED":
                self._authorization_required_calls += 1
            elif status_val == "AUTHORIZATION_DENIED":
                self._authorization_denied_calls += 1
            else:
                self._failed_executions += 1

    def record_cache_access(self, hit: bool) -> None:
        """Record schema cache hit or miss."""
        with self._lock:
            if hit:
                self._schema_cache_hits += 1
            else:
                self._schema_cache_misses += 1

    def get_metrics_snapshot(self) -> dict[str, Any]:
        """Return thread-safe dictionary snapshot of metrics."""
        with self._lock:
            avg_dur = (
                float(np.mean(self._processing_durations_ms))
                if self._processing_durations_ms
                else 0.0
            )

            return {
                "calls_generated": self._calls_generated,
                "calls_accepted": self._calls_accepted,
                "calls_rejected": self._calls_rejected,
                "unknown_tool_calls": self._unknown_tool_calls,
                "invalid_argument_calls": self._invalid_argument_calls,
                "authorization_required_calls": self._authorization_required_calls,
                "authorization_denied_calls": self._authorization_denied_calls,
                "successful_executions": self._successful_executions,
                "failed_executions": self._failed_executions,
                "schema_cache_hits": self._schema_cache_hits,
                "schema_cache_misses": self._schema_cache_misses,
                "average_processing_duration_ms": round(avg_dur, 2),
            }

    def reset(self) -> None:
        """Reset all metric counters."""
        with self._lock:
            self._calls_generated = 0
            self._calls_accepted = 0
            self._calls_rejected = 0
            self._unknown_tool_calls = 0
            self._invalid_argument_calls = 0
            self._authorization_required_calls = 0
            self._authorization_denied_calls = 0
            self._successful_executions = 0
            self._failed_executions = 0
            self._schema_cache_hits = 0
            self._schema_cache_misses = 0
            self._processing_durations_ms.clear()
