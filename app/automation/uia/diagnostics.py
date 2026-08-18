"""Diagnostic health reporting for the UI Automation subsystem."""

import sys
from typing import Any

from app.automation.models import UIAStatus
from app.automation.uia.metrics import UIAutomationMetrics
from app.automation.uia.window_resolver import WindowResolver

try:
    import pywinauto

    PYWINAUTO_AVAILABLE = True
    PYWINAUTO_VERSION = getattr(pywinauto, "__version__", "unknown")
except ImportError:
    PYWINAUTO_AVAILABLE = False
    PYWINAUTO_VERSION = "N/A"

try:
    import win32gui

    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False


class UIAutomationDiagnostics:
    """Generates health and diagnostic status reports for the UIA subsystem."""

    def __init__(
        self,
        window_resolver: WindowResolver | None = None,
        metrics: UIAutomationMetrics | None = None,
    ) -> None:
        self.window_resolver = window_resolver or WindowResolver()
        self.metrics = metrics or UIAutomationMetrics()

    def get_health_report(self) -> dict[str, Any]:
        """Generate structured status health report."""
        is_win = sys.platform == "win32"
        win_enum_avail = self.window_resolver.is_available()

        if is_win and PYWINAUTO_AVAILABLE and PYWIN32_AVAILABLE and win_enum_avail:
            status = UIAStatus.HEALTHY
        elif is_win and PYWINAUTO_AVAILABLE:
            status = UIAStatus.DEGRADED
        else:
            status = UIAStatus.UNAVAILABLE

        metrics_summary = self.metrics.get_metrics_summary()

        return {
            "status": status.value,
            "platform": sys.platform,
            "is_windows": is_win,
            "pywinauto": "AVAILABLE" if PYWINAUTO_AVAILABLE else "UNAVAILABLE",
            "pywinauto_version": PYWINAUTO_VERSION,
            "pywin32": "AVAILABLE" if PYWIN32_AVAILABLE else "UNAVAILABLE",
            "windows_enumeration": "AVAILABLE" if win_enum_avail else "UNAVAILABLE",
            "element_discovery": "AVAILABLE" if PYWINAUTO_AVAILABLE else "UNAVAILABLE",
            "tree_walker": "AVAILABLE",
            "pattern_support": "AVAILABLE" if PYWINAUTO_AVAILABLE else "UNAVAILABLE",
            "metrics": metrics_summary,
        }
