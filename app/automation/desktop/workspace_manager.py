"""Workspace topology layout capture and restoration service."""

from typing import Any

from app.automation.desktop.models import (
    DesktopWindow,
    WindowLayoutEntry,
    WindowState,
    WorkspaceLayout,
)
from app.automation.desktop.monitor_manager import MonitorManager
from app.automation.desktop.window_controller import WindowController


class WorkspaceManager:
    """Captures and restores desktop workspace window layouts."""

    def __init__(
        self,
        window_controller: WindowController | None = None,
        monitor_manager: MonitorManager | None = None,
    ) -> None:
        self.window_controller = window_controller or WindowController()
        self.monitor_manager = monitor_manager or MonitorManager()

    def capture_workspace_layout(self) -> WorkspaceLayout:
        """Capture snapshot of current desktop workspace topology."""
        monitors = self.monitor_manager.list_monitors()
        desktop_wins = self.window_controller.list_windows(include_hidden=False)

        entries: list[WindowLayoutEntry] = []
        for win in desktop_wins:
            if not win.title or win.width <= 0 or win.height <= 0:
                continue

            state = WindowState.RESTORED
            if win.is_minimized:
                state = WindowState.MINIMIZED
            elif win.is_maximized:
                state = WindowState.MAXIMIZED

            entries.append(
                WindowLayoutEntry(
                    hwnd=win.hwnd,
                    title=win.title,
                    process_name=win.process_name,
                    class_name=win.class_name,
                    state=state,
                    left=win.left,
                    top=win.top,
                    width=win.width,
                    height=win.height,
                    monitor_id=win.monitor_id,
                )
            )

        return WorkspaceLayout(monitors=monitors, windows=entries)

    def restore_workspace_layout(self, layout: WorkspaceLayout) -> dict[str, Any]:
        """Restore desktop workspace window layout. Skips missing windows safely without launching apps."""
        if not layout or not layout.windows:
            return {
                "status": "COMPLETED",
                "restored": 0,
                "skipped": 0,
                "failed": 0,
                "details": [],
            }

        current_windows = self.window_controller.list_windows(include_hidden=True)
        current_hwnd_map = {win.hwnd: win for win in current_windows}

        restored_count = 0
        skipped_count = 0
        failed_count = 0
        details: list[dict[str, Any]] = []

        for entry in layout.windows:
            target_win: DesktopWindow | None = None

            # 1. Match by exact HWND if still valid
            if entry.hwnd in current_hwnd_map:
                target_win = current_hwnd_map[entry.hwnd]
            else:
                # 2. Match by title and process_name
                for win in current_windows:
                    if (
                        win.title == entry.title
                        and win.process_name == entry.process_name
                    ):
                        target_win = win
                        break

            if not target_win:
                skipped_count += 1
                details.append(
                    {
                        "entry_title": entry.title,
                        "process_name": entry.process_name,
                        "status": "SKIPPED",
                        "reason": "Window not found on desktop.",
                    }
                )
                continue

            try:
                # Restore window state and geometry
                if entry.state == WindowState.MINIMIZED:
                    self.window_controller.minimize_window(target_win.hwnd)
                elif entry.state == WindowState.MAXIMIZED:
                    self.window_controller.maximize_window(target_win.hwnd)
                else:
                    self.window_controller.restore_window(target_win.hwnd)
                    self.window_controller.move_window(
                        target_win.hwnd, entry.left, entry.top
                    )
                    self.window_controller.resize_window(
                        target_win.hwnd, entry.width, entry.height
                    )

                restored_count += 1
                details.append(
                    {
                        "entry_title": entry.title,
                        "hwnd": target_win.hwnd,
                        "status": "RESTORED",
                    }
                )
            except Exception as exc:
                failed_count += 1
                details.append(
                    {
                        "entry_title": entry.title,
                        "hwnd": target_win.hwnd,
                        "status": "FAILED",
                        "error": str(exc),
                    }
                )

        return {
            "status": "COMPLETED",
            "restored": restored_count,
            "skipped": skipped_count,
            "failed": failed_count,
            "details": details,
        }
