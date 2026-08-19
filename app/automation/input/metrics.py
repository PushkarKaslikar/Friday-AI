"""Thread-safe telemetry metrics for Phase 6.2 input subsystem."""

import threading
from typing import Any


class InputMetrics:
    """Tracks non-sensitive operation counts, latencies, and status metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.total_operations: int = 0
        self.completed_operations: int = 0
        self.cancelled_operations: int = 0
        self.interrupted_operations: int = 0
        self.failsafe_aborts: int = 0
        self.failed_operations: int = 0
        self.mouse_moves: int = 0
        self.mouse_clicks: int = 0
        self.drag_operations: int = 0
        self.key_presses: int = 0
        self.hotkey_presses: int = 0
        self.typing_operations: int = 0
        self.native_backend_calls: int = 0
        self.pyautogui_backend_calls: int = 0
        self.total_latency_ms: float = 0.0

    def record_operation(
        self,
        op_type: str,
        status_str: str,
        backend_str: str,
        duration_ms: float,
        interrupted: bool = False,
        cancelled: bool = False,
        failsafe_triggered: bool = False,
    ) -> None:
        """Record completed input operation metrics."""
        with self._lock:
            self.total_operations += 1
            self.total_latency_ms += max(0.0, duration_ms)

            if backend_str == "PYAUTOGUI":
                self.pyautogui_backend_calls += 1
            else:
                self.native_backend_calls += 1

            if status_str == "COMPLETED":
                self.completed_operations += 1
            elif status_str == "CANCELLED" or cancelled:
                self.cancelled_operations += 1
            elif status_str == "INTERRUPTED" or interrupted:
                self.interrupted_operations += 1
            elif status_str == "FAILSAFE_ABORTED" or failsafe_triggered:
                self.failsafe_aborts += 1
            else:
                self.failed_operations += 1

            if "move" in op_type:
                self.mouse_moves += 1
            elif "click" in op_type:
                self.mouse_clicks += 1
            elif "drag" in op_type:
                self.drag_operations += 1
            elif "press_key" in op_type or "key_down" in op_type or "key_up" in op_type:
                self.key_presses += 1
            elif "hotkey" in op_type:
                self.hotkey_presses += 1
            elif "type" in op_type:
                self.typing_operations += 1

    def to_dict(self) -> dict[str, Any]:
        """Return snapshot dictionary of metrics."""
        with self._lock:
            avg_lat = (
                self.total_latency_ms / self.total_operations
                if self.total_operations > 0
                else 0.0
            )
            return {
                "total_operations": self.total_operations,
                "completed_operations": self.completed_operations,
                "cancelled_operations": self.cancelled_operations,
                "interrupted_operations": self.interrupted_operations,
                "failsafe_aborts": self.failsafe_aborts,
                "failed_operations": self.failed_operations,
                "mouse_moves": self.mouse_moves,
                "mouse_clicks": self.mouse_clicks,
                "drag_operations": self.drag_operations,
                "key_presses": self.key_presses,
                "hotkey_presses": self.hotkey_presses,
                "typing_operations": self.typing_operations,
                "native_backend_calls": self.native_backend_calls,
                "pyautogui_backend_calls": self.pyautogui_backend_calls,
                "average_latency_ms": round(avg_lat, 2),
            }

    def reset(self) -> None:
        """Reset all metric counters."""
        with self._lock:
            self.total_operations = 0
            self.completed_operations = 0
            self.cancelled_operations = 0
            self.interrupted_operations = 0
            self.failsafe_aborts = 0
            self.failed_operations = 0
            self.mouse_moves = 0
            self.mouse_clicks = 0
            self.drag_operations = 0
            self.key_presses = 0
            self.hotkey_presses = 0
            self.typing_operations = 0
            self.native_backend_calls = 0
            self.pyautogui_backend_calls = 0
            self.total_latency_ms = 0.0
