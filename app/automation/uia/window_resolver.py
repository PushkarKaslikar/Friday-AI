"""Window discovery and attachment resolver for Windows top-level application windows."""

import sys
from typing import Any

from app.automation.errors import AmbiguousWindowError, ProcessExitedError
from app.automation.models import (
    MatchMode,
    WindowCandidate,
    WindowSearchResult,
    WindowSearchStatus,
)
from app.logging import logger

try:
    import psutil
except ImportError:
    psutil = None

try:
    import win32gui
    import win32process

    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False


class WindowResolver:
    """Discovers, filters, and resolves top-level application windows on Windows operating systems."""

    def __init__(self) -> None:
        self._is_windows = sys.platform == "win32"

    def is_available(self) -> bool:
        """Check if native window resolution dependencies are available."""
        return self._is_windows and PYWIN32_AVAILABLE

    def _get_process_name(self, pid: int) -> str:
        """Helper to get process executable name by PID."""
        if not pid or pid == 0:
            return ""
        if psutil:
            try:
                p = psutil.Process(pid)
                return p.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return ""
        return ""

    def enumerate_windows(self, include_hidden: bool = False) -> list[WindowCandidate]:
        """Enumerate all top-level application windows."""
        candidates: list[WindowCandidate] = []
        if not self.is_available():
            logger.warning(
                "Window enumeration requested on unsupported platform or without pywin32."
            )
            return candidates

        def enum_window_callback(hwnd: int, extra: Any) -> bool:
            if not win32gui.IsWindow(hwnd):
                return True

            is_visible = bool(win32gui.IsWindowVisible(hwnd))
            if not is_visible and not include_hidden:
                return True

            title = win32gui.GetWindowText(hwnd) or ""
            # Filter out zero-length titled windows unless specifically including hidden
            if not title and not include_hidden:
                return True

            class_name = win32gui.GetClassName(hwnd) or ""
            is_enabled = bool(win32gui.IsWindowEnabled(hwnd))

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc_name = self._get_process_name(pid)

            candidate = WindowCandidate(
                hwnd=hwnd,
                title=title,
                process_id=pid,
                process_name=proc_name,
                class_name=class_name,
                is_visible=is_visible,
                is_enabled=is_enabled,
            )
            candidates.append(candidate)
            return True

        try:
            win32gui.EnumWindows(enum_window_callback, None)
        except Exception as exc:
            logger.error(f"Error enumerating windows: {exc}")

        return candidates

    def resolve_window(
        self,
        title: str | None = None,
        process_id: int | None = None,
        process_name: str | None = None,
        hwnd: int | None = None,
        match_mode: MatchMode = MatchMode.CONTAINS,
        include_hidden: bool = False,
    ) -> WindowSearchResult:
        """Filter candidates by HWND, PID, process_name, or title with ambiguity protection."""
        if process_id is not None and psutil:
            if not psutil.pid_exists(process_id):
                raise ProcessExitedError(
                    f"Process ID {process_id} does not exist or has exited.",
                    details={"process_id": process_id},
                )

        all_candidates = self.enumerate_windows(include_hidden=include_hidden)
        filtered = all_candidates

        # 1. HWND filter
        if hwnd is not None:
            filtered = [c for c in filtered if c.hwnd == hwnd]

        # 2. Process ID filter
        if process_id is not None:
            filtered = [c for c in filtered if c.process_id == process_id]

        # 3. Process name filter
        if process_name:
            p_name_lower = process_name.lower()
            filtered = [
                c
                for c in filtered
                if c.process_name and p_name_lower in c.process_name.lower()
            ]

        # 4. Title filter
        if title:
            filtered = [
                c for c in filtered if self._match_string(c.title, title, match_mode)
            ]

        if not filtered:
            return WindowSearchResult(
                status=WindowSearchStatus.NOT_FOUND,
                candidates=[],
                selected_hwnd=None,
                selected_candidate=None,
                diagnostics={
                    "query": {
                        "title": title,
                        "process_id": process_id,
                        "process_name": process_name,
                        "hwnd": hwnd,
                        "match_mode": (
                            match_mode.value
                            if isinstance(match_mode, MatchMode)
                            else match_mode
                        ),
                    }
                },
            )

        if len(filtered) == 1:
            match = filtered[0]
            return WindowSearchResult(
                status=WindowSearchStatus.FOUND,
                candidates=filtered,
                selected_hwnd=match.hwnd,
                selected_candidate=match,
                diagnostics={"match_count": 1},
            )

        # Multiple candidates match -> AMBIGUOUS
        return WindowSearchResult(
            status=WindowSearchStatus.AMBIGUOUS,
            candidates=filtered,
            selected_hwnd=None,
            selected_candidate=None,
            diagnostics={
                "match_count": len(filtered),
                "reason": "Multiple windows match the search criteria. Refine window criteria.",
            },
        )

    def attach_to_window(self, hwnd: int) -> WindowCandidate:
        """Attach to window directly by HWND."""
        res = self.resolve_window(hwnd=hwnd, include_hidden=True)
        if res.status == WindowSearchStatus.FOUND and res.selected_candidate:
            return res.selected_candidate
        raise AmbiguousWindowError(
            f"Window with HWND {hwnd} was not found.",
            details={"hwnd": hwnd, "status": res.status.value},
        )

    def attach_to_process(self, pid: int) -> WindowSearchResult:
        """Attach to process by PID."""
        return self.resolve_window(process_id=pid)

    def attach_by_title(
        self, title: str, match_mode: MatchMode = MatchMode.CONTAINS
    ) -> WindowSearchResult:
        """Attach by title string."""
        return self.resolve_window(title=title, match_mode=match_mode)

    def attach_by_process_name(self, name: str) -> WindowSearchResult:
        """Attach by process executable name."""
        return self.resolve_window(process_name=name)

    def _match_string(self, source: str, target: str, mode: MatchMode) -> bool:
        """Perform string matching according to MatchMode."""
        if not source and target:
            return False
        if mode == MatchMode.EXACT:
            return source == target
        elif mode == MatchMode.CASE_INSENSITIVE:
            return source.lower() == target.lower()
        elif mode == MatchMode.CONTAINS:
            return target.lower() in source.lower()
        elif mode == MatchMode.STARTS_WITH:
            return source.lower().startswith(target.lower())
        return target.lower() in source.lower()
