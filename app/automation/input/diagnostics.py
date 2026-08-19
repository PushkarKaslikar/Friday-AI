"""Subsystem health reporting for Phase 6.2 input engine."""

import sys
from typing import Any

from app.automation.input.failsafe import InputFailsafe
from app.automation.input.interruption_monitor import InterruptionMonitor
from app.automation.input.native_input import NativeInputBackend
from app.automation.input.pyautogui_fallback import PyAutoGUIInputBackend


class InputDiagnostics:
    """Generates structured health status reports for the input control subsystem."""

    def __init__(
        self,
        native_backend: NativeInputBackend | None = None,
        pyautogui_backend: PyAutoGUIInputBackend | None = None,
        failsafe: InputFailsafe | None = None,
        interruption_monitor: InterruptionMonitor | None = None,
    ) -> None:
        self.native_backend = native_backend or NativeInputBackend()
        self.pyautogui_backend = pyautogui_backend or PyAutoGUIInputBackend()
        self.failsafe = failsafe or InputFailsafe()
        self.interruption_monitor = interruption_monitor or InterruptionMonitor()

    def get_health_report(
        self, is_busy: bool = False, current_op: str | None = None
    ) -> dict[str, Any]:
        """Produce structured diagnostic health dictionary."""
        native_avail = self.native_backend.is_available()
        pyautogui_avail = self.pyautogui_backend.is_available()

        if native_avail and pyautogui_avail:
            status = "HEALTHY"
        elif native_avail or pyautogui_avail:
            status = "DEGRADED"
        else:
            status = "UNAVAILABLE"

        return {
            "status": status,
            "platform": sys.platform,
            "native_backend": "AVAILABLE" if native_avail else "UNAVAILABLE",
            "pyautogui_backend": "AVAILABLE" if pyautogui_avail else "UNAVAILABLE",
            "failsafe_enabled": self.failsafe.enabled,
            "interruption_detection_enabled": self.interruption_monitor.enabled,
            "channel_state": "BUSY" if is_busy else "IDLE",
            "active_operation": current_op or "NONE",
        }
