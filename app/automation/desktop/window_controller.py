"""Windows top-level window manipulation controller."""

import sys
import time

from app.automation.desktop.errors import (
    FocusDeniedError,
    InvalidGeometryError,
    WindowClosedError,
)
from app.automation.desktop.models import (
    DesktopWindow,
    SnapPosition,
    WindowOperationResult,
)
from app.automation.desktop.monitor_manager import MonitorManager
from app.automation.desktop.window_controller_interface import IWindowController
from app.automation.uia.window_resolver import WindowResolver
from app.logging import logger

try:
    import win32con
    import win32gui

    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False


class WindowController(IWindowController):
    """Controls top-level window discovery, focus, geometry manipulation, snapping, and normal close."""

    def __init__(
        self,
        window_resolver: WindowResolver | None = None,
        monitor_manager: MonitorManager | None = None,
    ) -> None:
        self.window_resolver = window_resolver or WindowResolver()
        self.monitor_manager = monitor_manager or MonitorManager()

    def _build_desktop_window(self, hwnd: int) -> DesktopWindow:
        """Construct DesktopWindow model for a given HWND handle."""
        if (
            not sys.platform == "win32"
            or not PYWIN32_AVAILABLE
            or not win32gui.IsWindow(hwnd)
        ):
            raise WindowClosedError(f"HWND handle {hwnd} is not a valid window.")

        active_hwnd = win32gui.GetForegroundWindow()
        is_active = hwnd == active_hwnd

        title = win32gui.GetWindowText(hwnd) or ""
        class_name = win32gui.GetClassName(hwnd) or ""
        is_visible = bool(win32gui.IsWindowVisible(hwnd))
        is_minimized = bool(win32gui.IsIconic(hwnd))
        try:
            placement = win32gui.GetWindowPlacement(hwnd)
            is_maximized = bool(placement[1] == win32con.SW_SHOWMAXIMIZED)
        except Exception:
            is_maximized = False

        rect = win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = rect
        width = max(0, right - left)
        height = max(0, bottom - top)

        process_id = 0
        process_name = ""
        try:
            cand = self.window_resolver.get_window_by_handle(hwnd)
            process_id = cand.process_id
            process_name = cand.process_name
        except Exception:
            pass

        mon = self.monitor_manager.get_monitor_for_window(hwnd)

        return DesktopWindow(
            hwnd=hwnd,
            title=title,
            process_id=process_id,
            process_name=process_name,
            class_name=class_name,
            is_visible=is_visible,
            is_minimized=is_minimized,
            is_maximized=is_maximized,
            is_active=is_active,
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            width=width,
            height=height,
            monitor_id=mon.monitor_id,
        )

    def list_windows(self, include_hidden: bool = False) -> list[DesktopWindow]:
        """List all top-level desktop windows."""
        candidates = self.window_resolver.enumerate_windows(
            include_hidden=include_hidden
        )
        windows: list[DesktopWindow] = []
        for cand in candidates:
            try:
                win = self._build_desktop_window(cand.hwnd)
                windows.append(win)
            except Exception:
                continue
        return windows

    def get_active_window(self) -> DesktopWindow | None:
        """Get DesktopWindow for active foreground window."""
        if sys.platform == "win32" and PYWIN32_AVAILABLE:
            try:
                hwnd = win32gui.GetForegroundWindow()
                if hwnd and hwnd > 0 and win32gui.IsWindow(hwnd):
                    return self._build_desktop_window(hwnd)
            except Exception as exc:
                logger.debug(f"Failed to query active foreground window: {exc}")
        return None

    def get_window_by_hwnd(self, hwnd: int) -> DesktopWindow:
        """Get DesktopWindow for specific HWND."""
        return self._build_desktop_window(hwnd)

    def focus_window(self, hwnd: int) -> WindowOperationResult:
        """Bring window to foreground and set focus."""
        t0 = time.perf_counter()
        if (
            sys.platform != "win32"
            or not PYWIN32_AVAILABLE
            or not win32gui.IsWindow(hwnd)
        ):
            raise WindowClosedError(f"Cannot focus invalid HWND handle: {hwnd}")

        prev_win = self._build_desktop_window(hwnd)
        prev_geom = {
            "left": prev_win.left,
            "top": prev_win.top,
            "width": prev_win.width,
            "height": prev_win.height,
        }

        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.05)

            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.05)
        except Exception as exc:
            raise FocusDeniedError(
                f"Could not focus window HWND {hwnd}: {exc}", cause=exc
            )

        new_win = self._build_desktop_window(hwnd)
        new_geom = {
            "left": new_win.left,
            "top": new_win.top,
            "width": new_win.width,
            "height": new_win.height,
        }
        duration_ms = (time.perf_counter() - t0) * 1000.0

        return WindowOperationResult(
            status="COMPLETED",
            hwnd=hwnd,
            operation="focus",
            previous_geometry=prev_geom,
            new_geometry=new_geom,
            monitor_id=new_win.monitor_id,
            reason_code="SUCCESS",
            duration_ms=round(duration_ms, 2),
        )

    def minimize_window(self, hwnd: int) -> WindowOperationResult:
        """Minimize window."""
        t0 = time.perf_counter()
        if (
            sys.platform != "win32"
            or not PYWIN32_AVAILABLE
            or not win32gui.IsWindow(hwnd)
        ):
            raise WindowClosedError(f"Cannot minimize invalid HWND handle: {hwnd}")

        prev_win = self._build_desktop_window(hwnd)
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

        duration_ms = (time.perf_counter() - t0) * 1000.0
        return WindowOperationResult(
            status="COMPLETED",
            hwnd=hwnd,
            operation="minimize",
            previous_geometry={
                "left": prev_win.left,
                "top": prev_win.top,
                "width": prev_win.width,
                "height": prev_win.height,
            },
            new_geometry=None,
            monitor_id=prev_win.monitor_id,
            reason_code="SUCCESS",
            duration_ms=round(duration_ms, 2),
        )

    def maximize_window(self, hwnd: int) -> WindowOperationResult:
        """Maximize window."""
        t0 = time.perf_counter()
        if (
            sys.platform != "win32"
            or not PYWIN32_AVAILABLE
            or not win32gui.IsWindow(hwnd)
        ):
            raise WindowClosedError(f"Cannot maximize invalid HWND handle: {hwnd}")

        prev_win = self._build_desktop_window(hwnd)
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

        new_win = self._build_desktop_window(hwnd)
        duration_ms = (time.perf_counter() - t0) * 1000.0
        return WindowOperationResult(
            status="COMPLETED",
            hwnd=hwnd,
            operation="maximize",
            previous_geometry={
                "left": prev_win.left,
                "top": prev_win.top,
                "width": prev_win.width,
                "height": prev_win.height,
            },
            new_geometry={
                "left": new_win.left,
                "top": new_win.top,
                "width": new_win.width,
                "height": new_win.height,
            },
            monitor_id=new_win.monitor_id,
            reason_code="SUCCESS",
            duration_ms=round(duration_ms, 2),
        )

    def restore_window(self, hwnd: int) -> WindowOperationResult:
        """Restore window to normal state."""
        t0 = time.perf_counter()
        if (
            sys.platform != "win32"
            or not PYWIN32_AVAILABLE
            or not win32gui.IsWindow(hwnd)
        ):
            raise WindowClosedError(f"Cannot restore invalid HWND handle: {hwnd}")

        prev_win = self._build_desktop_window(hwnd)
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        new_win = self._build_desktop_window(hwnd)
        duration_ms = (time.perf_counter() - t0) * 1000.0
        return WindowOperationResult(
            status="COMPLETED",
            hwnd=hwnd,
            operation="restore",
            previous_geometry={
                "left": prev_win.left,
                "top": prev_win.top,
                "width": prev_win.width,
                "height": prev_win.height,
            },
            new_geometry={
                "left": new_win.left,
                "top": new_win.top,
                "width": new_win.width,
                "height": new_win.height,
            },
            monitor_id=new_win.monitor_id,
            reason_code="SUCCESS",
            duration_ms=round(duration_ms, 2),
        )

    def move_window(self, hwnd: int, x: int, y: int) -> WindowOperationResult:
        """Move window to absolute virtual screen coordinates."""
        t0 = time.perf_counter()
        if (
            sys.platform != "win32"
            or not PYWIN32_AVAILABLE
            or not win32gui.IsWindow(hwnd)
        ):
            raise WindowClosedError(f"Cannot move invalid HWND handle: {hwnd}")

        prev_win = self._build_desktop_window(hwnd)

        # Retain current width and height
        win32gui.SetWindowPos(
            hwnd,
            0,
            int(x),
            int(y),
            prev_win.width,
            prev_win.height,
            win32con.SWP_NOZORDER,
        )

        new_win = self._build_desktop_window(hwnd)
        duration_ms = (time.perf_counter() - t0) * 1000.0
        return WindowOperationResult(
            status="COMPLETED",
            hwnd=hwnd,
            operation="move",
            previous_geometry={
                "left": prev_win.left,
                "top": prev_win.top,
                "width": prev_win.width,
                "height": prev_win.height,
            },
            new_geometry={
                "left": new_win.left,
                "top": new_win.top,
                "width": new_win.width,
                "height": new_win.height,
            },
            monitor_id=new_win.monitor_id,
            reason_code="SUCCESS",
            duration_ms=round(duration_ms, 2),
        )

    def resize_window(
        self, hwnd: int, width: int, height: int
    ) -> WindowOperationResult:
        """Resize window dimensions."""
        t0 = time.perf_counter()
        if (
            sys.platform != "win32"
            or not PYWIN32_AVAILABLE
            or not win32gui.IsWindow(hwnd)
        ):
            raise WindowClosedError(f"Cannot resize invalid HWND handle: {hwnd}")

        if width <= 0 or height <= 0:
            raise InvalidGeometryError(
                f"Invalid dimensions: width={width}, height={height}"
            )

        prev_win = self._build_desktop_window(hwnd)

        # Retain current left and top
        win32gui.SetWindowPos(
            hwnd,
            0,
            prev_win.left,
            prev_win.top,
            int(width),
            int(height),
            win32con.SWP_NOZORDER,
        )

        new_win = self._build_desktop_window(hwnd)
        duration_ms = (time.perf_counter() - t0) * 1000.0
        return WindowOperationResult(
            status="COMPLETED",
            hwnd=hwnd,
            operation="resize",
            previous_geometry={
                "left": prev_win.left,
                "top": prev_win.top,
                "width": prev_win.width,
                "height": prev_win.height,
            },
            new_geometry={
                "left": new_win.left,
                "top": new_win.top,
                "width": new_win.width,
                "height": new_win.height,
            },
            monitor_id=new_win.monitor_id,
            reason_code="SUCCESS",
            duration_ms=round(duration_ms, 2),
        )

    def snap_window(self, hwnd: int, position: SnapPosition) -> WindowOperationResult:
        """Snap window to monitor work area position."""
        t0 = time.perf_counter()
        if (
            sys.platform != "win32"
            or not PYWIN32_AVAILABLE
            or not win32gui.IsWindow(hwnd)
        ):
            raise WindowClosedError(f"Cannot snap invalid HWND handle: {hwnd}")

        prev_win = self._build_desktop_window(hwnd)
        mon = self.monitor_manager.get_monitor_for_window(hwnd)

        wl, wt, wr, wb = mon.work_left, mon.work_top, mon.work_right, mon.work_bottom
        total_w = max(1, wr - wl)
        total_h = max(1, wb - wt)
        half_w = total_w // 2
        half_h = total_h // 2

        if position == SnapPosition.LEFT:
            nx, ny, nw, nh = wl, wt, half_w, total_h
        elif position == SnapPosition.RIGHT:
            nx, ny, nw, nh = wl + half_w, wt, half_w, total_h
        elif position == SnapPosition.TOP:
            nx, ny, nw, nh = wl, wt, total_w, half_h
        elif position == SnapPosition.BOTTOM:
            nx, ny, nw, nh = wl, wt + half_h, total_w, half_h
        elif position == SnapPosition.TOP_LEFT:
            nx, ny, nw, nh = wl, wt, half_w, half_h
        elif position == SnapPosition.TOP_RIGHT:
            nx, ny, nw, nh = wl + half_w, wt, half_w, half_h
        elif position == SnapPosition.BOTTOM_LEFT:
            nx, ny, nw, nh = wl, wt + half_h, half_w, half_h
        elif position == SnapPosition.BOTTOM_RIGHT:
            nx, ny, nw, nh = wl + half_w, wt + half_h, half_w, half_h
        elif position == SnapPosition.CENTER:
            nw = (total_w * 3) // 4
            nh = (total_h * 3) // 4
            nx = wl + (total_w - nw) // 2
            ny = wt + (total_h - nh) // 2
        else:  # FULLSCREEN
            nx, ny, nw, nh = wl, wt, total_w, total_h

        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        win32gui.SetWindowPos(hwnd, 0, nx, ny, nw, nh, win32con.SWP_NOZORDER)

        new_win = self._build_desktop_window(hwnd)
        duration_ms = (time.perf_counter() - t0) * 1000.0

        return WindowOperationResult(
            status="COMPLETED",
            hwnd=hwnd,
            operation=f"snap_{position.value.lower()}",
            previous_geometry={
                "left": prev_win.left,
                "top": prev_win.top,
                "width": prev_win.width,
                "height": prev_win.height,
            },
            new_geometry={
                "left": new_win.left,
                "top": new_win.top,
                "width": new_win.width,
                "height": new_win.height,
            },
            monitor_id=mon.monitor_id,
            reason_code="SUCCESS",
            duration_ms=round(duration_ms, 2),
        )

    def close_window(self, hwnd: int) -> WindowOperationResult:
        """Send standard close request (WM_CLOSE) to window without process termination."""
        t0 = time.perf_counter()
        if (
            sys.platform != "win32"
            or not PYWIN32_AVAILABLE
            or not win32gui.IsWindow(hwnd)
        ):
            raise WindowClosedError(f"Cannot close invalid HWND handle: {hwnd}")

        prev_win = self._build_desktop_window(hwnd)
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

        duration_ms = (time.perf_counter() - t0) * 1000.0
        return WindowOperationResult(
            status="COMPLETED",
            hwnd=hwnd,
            operation="close",
            previous_geometry={
                "left": prev_win.left,
                "top": prev_win.top,
                "width": prev_win.width,
                "height": prev_win.height,
            },
            new_geometry=None,
            monitor_id=prev_win.monitor_id,
            reason_code="SUCCESS",
            duration_ms=round(duration_ms, 2),
        )
