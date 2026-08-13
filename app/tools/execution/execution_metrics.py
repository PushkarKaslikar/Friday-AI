"""Real-time execution metrics aggregator."""

import threading
from typing import Any

from app.tools.models.errors import ToolErrorCode
from app.tools.models.result import ToolResult


class ExecutionMetrics:
    """Thread-safe metrics aggregator for tool execution statistics."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        self.cancelled_executions = 0
        self.timed_out_executions = 0
        self.auth_denied_executions = 0
        self.retry_count = 0

        self.total_duration = 0.0
        self.min_duration = float("inf")
        self.max_duration = 0.0

    def record_execution(self, result: ToolResult, retries: int = 0) -> None:
        """Record a completed or failed ToolResult stats payload."""
        with self._lock:
            self.total_executions += 1
            self.retry_count += retries
            duration = max(0.0, result.execution_duration)
            self.total_duration += duration

            self.min_duration = min(self.min_duration, duration)
            self.max_duration = max(self.max_duration, duration)

            if result.success:
                self.successful_executions += 1
            else:
                self.failed_executions += 1
                if result.error_code == ToolErrorCode.TIMEOUT:
                    self.timed_out_executions += 1
                elif result.error_code == ToolErrorCode.CANCELLED:
                    self.cancelled_executions += 1
                elif result.error_code in (
                    ToolErrorCode.PERMISSION_DENIED,
                    ToolErrorCode.AUTHORIZATION_REQUIRED,
                ):
                    self.auth_denied_executions += 1

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get summary snapshot dictionary of metrics."""
        with self._lock:
            avg_dur = (
                round(self.total_duration / self.total_executions, 4)
                if self.total_executions > 0
                else 0.0
            )
            min_dur = (
                round(self.min_duration, 4)
                if self.min_duration != float("inf")
                else 0.0
            )

            return {
                "total_executions": self.total_executions,
                "successful_executions": self.successful_executions,
                "failed_executions": self.failed_executions,
                "cancelled_executions": self.cancelled_executions,
                "timed_out_executions": self.timed_out_executions,
                "auth_denied_executions": self.auth_denied_executions,
                "retry_count": self.retry_count,
                "avg_duration_sec": avg_dur,
                "min_duration_sec": min_dur,
                "max_duration_sec": round(self.max_duration, 4),
            }

    def reset(self) -> None:
        """Reset metrics counters."""
        with self._lock:
            self.total_executions = 0
            self.successful_executions = 0
            self.failed_executions = 0
            self.cancelled_executions = 0
            self.timed_out_executions = 0
            self.auth_denied_executions = 0
            self.retry_count = 0
            self.total_duration = 0.0
            self.min_duration = float("inf")
            self.max_duration = 0.0
