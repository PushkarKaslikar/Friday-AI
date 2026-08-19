"""Multi-monitor topology discovery and work area resolution service."""

import sys

from app.automation.desktop.errors import MonitorNotFoundError
from app.automation.desktop.models import MonitorInfo
from app.logging import logger

try:
    import win32api
    import win32con
    import win32gui

    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False


class MonitorManager:
    """Manages physical display monitors, primary monitor selection, and work area boundaries."""

    def list_monitors(self) -> list[MonitorInfo]:
        """Enumerate all connected physical display monitors."""
        monitors: list[MonitorInfo] = []

        if sys.platform == "win32" and PYWIN32_AVAILABLE:
            try:
                mon_handles = win32api.EnumDisplayMonitors()
                for idx, (h_mon, h_dc, rect) in enumerate(mon_handles):
                    info = win32api.GetMonitorInfo(h_mon)
                    mon_rect = info.get("Monitor", rect)
                    work_rect = info.get("Work", rect)
                    flags = info.get("Flags", 0)

                    is_primary = bool(flags & win32con.MONITORINFOF_PRIMARY) or (
                        mon_rect[0] == 0 and mon_rect[1] == 0
                    )

                    x, y, x2, y2 = mon_rect
                    width = max(1, x2 - x)
                    height = max(1, y2 - y)

                    wx1, wy1, wx2, wy2 = work_rect

                    monitors.append(
                        MonitorInfo(
                            monitor_id=idx,
                            is_primary=is_primary,
                            x=x,
                            y=y,
                            width=width,
                            height=height,
                            work_left=wx1,
                            work_top=wy1,
                            work_right=wx2,
                            work_bottom=wy2,
                        )
                    )
            except Exception as exc:
                logger.debug(f"Failed to enumerate Win32 display monitors: {exc}")

        if not monitors:
            # Fallback single 1080p monitor
            monitors.append(
                MonitorInfo(
                    monitor_id=0,
                    is_primary=True,
                    x=0,
                    y=0,
                    width=1920,
                    height=1080,
                    work_left=0,
                    work_top=0,
                    work_right=1920,
                    work_bottom=1040,
                )
            )

        return monitors

    def get_primary_monitor(self) -> MonitorInfo:
        """Return primary monitor information."""
        monitors = self.list_monitors()
        for mon in monitors:
            if mon.is_primary:
                return mon
        return monitors[0]

    def get_monitor_by_id(self, monitor_id: int) -> MonitorInfo:
        """Get MonitorInfo for a specific monitor index."""
        monitors = self.list_monitors()
        for mon in monitors:
            if mon.monitor_id == monitor_id:
                return mon
        raise MonitorNotFoundError(f"Monitor with ID {monitor_id} not found.")

    def get_monitor_for_point(self, x: int, y: int) -> MonitorInfo:
        """Identify which monitor contains the specified screen coordinate."""
        monitors = self.list_monitors()
        for mon in monitors:
            if mon.x <= x < (mon.x + mon.width) and mon.y <= y < (mon.y + mon.height):
                return mon
        return self.get_primary_monitor()

    def get_monitor_for_window(self, hwnd: int) -> MonitorInfo:
        """Identify which monitor contains the given HWND window handle."""
        if sys.platform == "win32" and PYWIN32_AVAILABLE and hwnd > 0:
            try:
                rect = win32gui.GetWindowRect(hwnd)
                cx = rect[0] + ((rect[2] - rect[0]) // 2)
                cy = rect[1] + ((rect[3] - rect[1]) // 2)
                return self.get_monitor_for_point(cx, cy)
            except Exception as exc:
                logger.debug(f"Failed to get window rect for HWND {hwnd}: {exc}")
        return self.get_primary_monitor()
