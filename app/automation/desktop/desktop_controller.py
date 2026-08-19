"""Main DesktopController coordinator service for Phase 6.3."""

import time
from typing import Any

from app.automation.desktop.clipboard_manager import ClipboardManager
from app.automation.desktop.diagnostics import DesktopDiagnostics
from app.automation.desktop.metrics import DesktopMetrics
from app.automation.desktop.models import (
    ClipboardResult,
    DesktopSnapshot,
    ScreenCaptureResult,
    SnapPosition,
    WindowOperationResult,
    WorkspaceLayout,
)
from app.automation.desktop.monitor_manager import MonitorManager
from app.automation.desktop.screen_capturer import ScreenCapturer
from app.automation.desktop.virtual_desktop import VirtualDesktopManager
from app.automation.desktop.window_controller import WindowController
from app.automation.desktop.workspace_manager import WorkspaceManager


class DesktopController:
    """Coordinator service managing desktop windows, monitors, virtual desktops, workspace topology, screen capture, and safe clipboard operations."""

    def __init__(
        self,
        window_controller: WindowController | None = None,
        monitor_manager: MonitorManager | None = None,
        virtual_desktop_manager: VirtualDesktopManager | None = None,
        workspace_manager: WorkspaceManager | None = None,
        screen_capturer: ScreenCapturer | None = None,
        clipboard_manager: ClipboardManager | None = None,
        metrics: DesktopMetrics | None = None,
        diagnostics: DesktopDiagnostics | None = None,
    ) -> None:
        self.window_controller = window_controller or WindowController()
        self.monitor_manager = monitor_manager or MonitorManager()
        self.virtual_desktop_manager = (
            virtual_desktop_manager or VirtualDesktopManager()
        )
        self.workspace_manager = workspace_manager or WorkspaceManager(
            window_controller=self.window_controller,
            monitor_manager=self.monitor_manager,
        )
        self.screen_capturer = screen_capturer or ScreenCapturer(
            monitor_manager=self.monitor_manager
        )
        self.clipboard_manager = clipboard_manager or ClipboardManager()
        self.metrics = metrics or DesktopMetrics()
        self.diagnostics = diagnostics or DesktopDiagnostics(
            window_controller=self.window_controller,
            monitor_manager=self.monitor_manager,
            virtual_desktop_manager=self.virtual_desktop_manager,
            screen_capturer=self.screen_capturer,
            clipboard_manager=self.clipboard_manager,
        )

    def get_desktop_snapshot(self) -> DesktopSnapshot:
        """Produce safe aggregated DesktopSnapshot metadata without raw screenshot bytes or clipboard text."""
        t0 = time.perf_counter()
        active_win = self.window_controller.get_active_window()
        windows = self.window_controller.list_windows(include_hidden=False)
        monitors = self.monitor_manager.list_monitors()
        vdesktop = self.virtual_desktop_manager.get_virtual_desktop_info()
        cb_fmt = self.clipboard_manager.inspect_format()

        duration_ms = (time.perf_counter() - t0) * 1000.0
        self.metrics.record_operation("get_desktop_snapshot", "COMPLETED", duration_ms)

        return DesktopSnapshot(
            active_window=active_win,
            windows=windows,
            monitors=monitors,
            virtual_desktop=vdesktop,
            clipboard_format=cb_fmt,
            timestamp=time.time(),
        )

    def focus_window(self, hwnd: int) -> WindowOperationResult:
        """Focus target window."""
        t0 = time.perf_counter()
        try:
            res = self.window_controller.focus_window(hwnd)
            self.metrics.record_operation(
                "focus_window", res.status, (time.perf_counter() - t0) * 1000.0
            )
            return res
        except Exception:
            self.metrics.record_operation(
                "focus_window", "FAILED", (time.perf_counter() - t0) * 1000.0
            )
            raise

    def snap_window(self, hwnd: int, position: SnapPosition) -> WindowOperationResult:
        """Snap target window."""
        t0 = time.perf_counter()
        try:
            res = self.window_controller.snap_window(hwnd, position)
            self.metrics.record_operation(
                "snap_window", res.status, (time.perf_counter() - t0) * 1000.0
            )
            return res
        except Exception:
            self.metrics.record_operation(
                "snap_window", "FAILED", (time.perf_counter() - t0) * 1000.0
            )
            raise

    def capture_workspace_layout(self) -> WorkspaceLayout:
        """Capture workspace topology layout."""
        t0 = time.perf_counter()
        try:
            layout = self.workspace_manager.capture_workspace_layout()
            self.metrics.record_operation(
                "capture_workspace_layout",
                "COMPLETED",
                (time.perf_counter() - t0) * 1000.0,
            )
            return layout
        except Exception:
            self.metrics.record_operation(
                "capture_workspace_layout",
                "FAILED",
                (time.perf_counter() - t0) * 1000.0,
            )
            raise

    def restore_workspace_layout(self, layout: WorkspaceLayout) -> dict[str, Any]:
        """Restore workspace topology layout."""
        t0 = time.perf_counter()
        try:
            res = self.workspace_manager.restore_workspace_layout(layout)
            self.metrics.record_operation(
                "restore_workspace_layout",
                res.get("status", "COMPLETED"),
                (time.perf_counter() - t0) * 1000.0,
            )
            return res
        except Exception:
            self.metrics.record_operation(
                "restore_workspace_layout",
                "FAILED",
                (time.perf_counter() - t0) * 1000.0,
            )
            raise

    def capture_screen(self, monitor_id: int | None = None) -> ScreenCaptureResult:
        """Capture in-memory screenshot of full screen or specified monitor."""
        t0 = time.perf_counter()
        try:
            if monitor_id is not None:
                res = self.screen_capturer.capture_monitor(monitor_id)
            else:
                res = self.screen_capturer.capture_all_monitors()
            self.metrics.record_operation(
                "capture_screen", res.status, (time.perf_counter() - t0) * 1000.0
            )
            return res
        except Exception:
            self.metrics.record_operation(
                "capture_screen", "FAILED", (time.perf_counter() - t0) * 1000.0
            )
            raise

    def read_clipboard_text(self, mask_secrets: bool = True) -> ClipboardResult:
        """Read safe text from clipboard with secret masking."""
        t0 = time.perf_counter()
        try:
            res = self.clipboard_manager.get_text(mask_secrets=mask_secrets)
            self.metrics.record_operation(
                "read_clipboard_text", res.status, (time.perf_counter() - t0) * 1000.0
            )
            return res
        except Exception:
            self.metrics.record_operation(
                "read_clipboard_text", "FAILED", (time.perf_counter() - t0) * 1000.0
            )
            raise

    def write_clipboard_text(self, text: str) -> ClipboardResult:
        """Write text to clipboard."""
        t0 = time.perf_counter()
        try:
            res = self.clipboard_manager.set_text(text)
            self.metrics.record_operation(
                "write_clipboard_text", res.status, (time.perf_counter() - t0) * 1000.0
            )
            return res
        except Exception:
            self.metrics.record_operation(
                "write_clipboard_text", "FAILED", (time.perf_counter() - t0) * 1000.0
            )
            raise
