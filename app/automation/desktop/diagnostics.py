"""Subsystem health reporting for Phase 6.3 desktop control engine."""

import sys
from typing import Any

from app.automation.desktop.clipboard_manager import ClipboardManager
from app.automation.desktop.monitor_manager import MonitorManager
from app.automation.desktop.screen_capturer import ScreenCapturer
from app.automation.desktop.virtual_desktop import VirtualDesktopManager
from app.automation.desktop.window_controller import WindowController


class DesktopDiagnostics:
    """Generates structured health status reports for the desktop control subsystem."""

    def __init__(
        self,
        window_controller: WindowController | None = None,
        monitor_manager: MonitorManager | None = None,
        virtual_desktop_manager: VirtualDesktopManager | None = None,
        screen_capturer: ScreenCapturer | None = None,
        clipboard_manager: ClipboardManager | None = None,
    ) -> None:
        self.window_controller = window_controller or WindowController()
        self.monitor_manager = monitor_manager or MonitorManager()
        self.virtual_desktop_manager = (
            virtual_desktop_manager or VirtualDesktopManager()
        )
        self.screen_capturer = screen_capturer or ScreenCapturer()
        self.clipboard_manager = clipboard_manager or ClipboardManager()

    def get_health_report(self) -> dict[str, Any]:
        """Produce structured diagnostic health dictionary."""
        is_win32 = sys.platform == "win32"
        capturer_avail = self.screen_capturer.is_available()
        clipboard_avail = self.clipboard_manager.is_available()
        vdesktop_info = self.virtual_desktop_manager.get_virtual_desktop_info()

        monitors = self.monitor_manager.list_monitors()

        if is_win32 and capturer_avail and clipboard_avail:
            status = "HEALTHY"
        elif is_win32 or capturer_avail or clipboard_avail:
            status = "DEGRADED"
        else:
            status = "UNAVAILABLE"

        return {
            "status": status,
            "platform": sys.platform,
            "win32_api": "AVAILABLE" if is_win32 else "UNAVAILABLE",
            "window_control": "AVAILABLE" if is_win32 else "UNAVAILABLE",
            "monitor_manager": "AVAILABLE",
            "monitor_count": len(monitors),
            "virtual_desktop": (
                "AVAILABLE" if vdesktop_info.is_available else "UNSUPPORTED"
            ),
            "screen_capture": "AVAILABLE" if capturer_avail else "UNAVAILABLE",
            "clipboard": "AVAILABLE" if clipboard_avail else "UNAVAILABLE",
        }
