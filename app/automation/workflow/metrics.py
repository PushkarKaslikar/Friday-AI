"""Telemetry counters and performance metrics for Phase 6.5 Workflow Engine Subsystem."""

import threading
from typing import Any


class WorkflowMetrics:
    """Thread-safe non-sensitive metric counter tracker for workflow execution."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._started = 0
        self._completed = 0
        self._failed = 0
        self._cancelled = 0
        self._interrupted = 0
        self._aborted = 0
        self._steps_executed = 0
        self._steps_verified = 0
        self._verification_failures = 0
        self._retries = 0
        self._recoveries = 0
        self._timeouts = 0
        self._resource_busy = 0

    def increment_started(self) -> None:
        with self._lock:
            self._started += 1

    def increment_completed(self) -> None:
        with self._lock:
            self._completed += 1

    def increment_failed(self) -> None:
        with self._lock:
            self._failed += 1

    def increment_cancelled(self) -> None:
        with self._lock:
            self._cancelled += 1

    def increment_interrupted(self) -> None:
        with self._lock:
            self._interrupted += 1

    def increment_aborted(self) -> None:
        with self._lock:
            self._aborted += 1

    def increment_steps_executed(self) -> None:
        with self._lock:
            self._steps_executed += 1

    def increment_steps_verified(self) -> None:
        with self._lock:
            self._steps_verified += 1

    def increment_verification_failures(self) -> None:
        with self._lock:
            self._verification_failures += 1

    def increment_retries(self) -> None:
        with self._lock:
            self._retries += 1

    def increment_recoveries(self) -> None:
        with self._lock:
            self._recoveries += 1

    def increment_timeouts(self) -> None:
        with self._lock:
            self._timeouts += 1

    def increment_resource_busy(self) -> None:
        with self._lock:
            self._resource_busy += 1

    def get_metrics_snapshot(self) -> dict[str, Any]:
        """Return atomic snapshot dictionary of telemetry metrics."""
        with self._lock:
            return {
                "workflows_started": self._started,
                "workflows_completed": self._completed,
                "workflows_failed": self._failed,
                "workflows_cancelled": self._cancelled,
                "workflows_interrupted": self._interrupted,
                "workflows_aborted": self._aborted,
                "steps_executed": self._steps_executed,
                "steps_verified": self._steps_verified,
                "verification_failures": self._verification_failures,
                "retries_count": self._retries,
                "recoveries_count": self._recoveries,
                "timeouts_count": self._timeouts,
                "resource_busy_count": self._resource_busy,
            }
