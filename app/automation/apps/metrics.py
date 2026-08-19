"""Application Adapters Telemetry & Metrics Tracker."""

import threading
import time
from typing import Any


class ApplicationAdapterMetrics:
    """Non-sensitive operation telemetry tracker for Phase 6.4 Application Adapters."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total_resolutions = 0
        self._total_launches = 0
        self._total_attaches = 0
        self._total_explorer_ops = 0
        self._total_terminal_ops = 0
        self._total_failures = 0
        self._operations: dict[str, dict[str, Any]] = {}

    def record_operation(
        self, op_type: str, op_name: str, status: str, duration_ms: float
    ) -> None:
        """Record an operation metric entry cleanly without private parameters or content."""
        with self._lock:
            if op_type == "resolution":
                self._total_resolutions += 1
            elif op_type == "launch":
                self._total_launches += 1
            elif op_type == "attach":
                self._total_attaches += 1
            elif op_type == "explorer":
                self._total_explorer_ops += 1
            elif op_type == "terminal":
                self._total_terminal_ops += 1

            if status not in ("SUCCESS", "COMPLETED"):
                self._total_failures += 1

            entry = self._operations.setdefault(
                op_name,
                {
                    "count": 0,
                    "success": 0,
                    "failed": 0,
                    "total_duration_ms": 0.0,
                    "last_timestamp": 0.0,
                },
            )
            entry["count"] += 1
            if status in ("SUCCESS", "COMPLETED"):
                entry["success"] += 1
            else:
                entry["failed"] += 1
            entry["total_duration_ms"] += duration_ms
            entry["last_timestamp"] = time.time()

    def get_summary(self) -> dict[str, Any]:
        """Return non-sensitive telemetry metrics summary dictionary."""
        with self._lock:
            return {
                "total_resolutions": self._total_resolutions,
                "total_launches": self._total_launches,
                "total_attaches": self._total_attaches,
                "total_explorer_ops": self._total_explorer_ops,
                "total_terminal_ops": self._total_terminal_ops,
                "total_failures": self._total_failures,
                "operation_types_count": len(self._operations),
            }
