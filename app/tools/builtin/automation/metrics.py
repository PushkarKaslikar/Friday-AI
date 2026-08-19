"""Telemetry metrics counter tracker for Phase 6.6 Automation Tool Suite."""

import threading
from typing import Any


class AutomationToolMetrics:
    """Thread-safe non-sensitive metric counter tracker for automation tools."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._invocations = 0
        self._success = 0
        self._failed = 0
        self._denied = 0
        self._confirmation_required = 0
        self._interrupted = 0
        self._failsafe_aborted = 0
        self._verification_failed = 0
        self._timeouts = 0

    def increment_invocation(self) -> None:
        with self._lock:
            self._invocations += 1

    def increment_success(self) -> None:
        with self._lock:
            self._success += 1

    def increment_failed(self) -> None:
        with self._lock:
            self._failed += 1

    def increment_denied(self) -> None:
        with self._lock:
            self._denied += 1

    def increment_confirmation_required(self) -> None:
        with self._lock:
            self._confirmation_required += 1

    def increment_interrupted(self) -> None:
        with self._lock:
            self._interrupted += 1

    def increment_failsafe_aborted(self) -> None:
        with self._lock:
            self._failsafe_aborted += 1

    def increment_verification_failed(self) -> None:
        with self._lock:
            self._verification_failed += 1

    def increment_timeouts(self) -> None:
        with self._lock:
            self._timeouts += 1

    def get_metrics_snapshot(self) -> dict[str, Any]:
        """Return atomic snapshot dictionary of telemetry metrics."""
        with self._lock:
            return {
                "invocations_count": self._invocations,
                "success_count": self._success,
                "failed_count": self._failed,
                "denied_count": self._denied,
                "confirmation_required_count": self._confirmation_required,
                "interrupted_count": self._interrupted,
                "failsafe_aborted_count": self._failsafe_aborted,
                "verification_failed_count": self._verification_failed,
                "timeouts_count": self._timeouts,
            }
