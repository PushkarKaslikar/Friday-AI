# Phase 6.3 Implementation Report — Window Management, Desktop Control, Clipboard & Screen Inspection Engine

## Subsystem Architecture Overview

Phase 6.3 implements Friday AI Assistant's foundational desktop control, window management, multi-monitor topology discovery, workspace layout snapshotting and restoration, in-memory screen capture (`mss`), and safe clipboard reading and writing with automatic secret masking. The subsystem resides in `app/automation/desktop/`.

### Component Hierarchy

```
                      Windows Desktop
                             |
         +-------------------+-------------------+
         |                   |                   |
         v                   v                   v
   WindowControl       ScreenCapture      ClipboardManager
   (Win32 User32)         (mss)         (win32clipboard)
         |                   |                   |
         +-------------------+-------------------+
                             |
                             v
                     DesktopController
```

---

## Deliverables & Components

### 1. Domain Models & Exceptions (`app/automation/desktop/models.py`, `errors.py`)
- `WindowState`: Enum (`ACTIVE`, `VISIBLE`, `MINIMIZED`, `MAXIMIZED`, `RESTORED`, `CLOSED`, `HIDDEN`).
- `SnapPosition`: Enum (`LEFT`, `RIGHT`, `TOP`, `BOTTOM`, `TOP_LEFT`, `TOP_RIGHT`, `BOTTOM_LEFT`, `BOTTOM_RIGHT`, `CENTER`, `FULLSCREEN`).
- `ClipboardFormat`: Enum (`TEXT`, `UNICODE_TEXT`, `HTML`, `FILE_LIST`, `EMPTY`, `UNSUPPORTED`).
- `DesktopWindow`: Detailed window representation (hwnd, title, process_id, process_name, class_name, is_visible, is_minimized, is_maximized, is_active, left, top, right, bottom, width, height, monitor_id).
- `MonitorInfo`: Multi-monitor model (monitor_id, is_primary, x, y, width, height, work_left, work_top, work_right, work_bottom, scale_factor).
- `VirtualDesktopInfo`: Virtual desktop model (is_available, current_desktop_id, total_desktops, is_window_on_current).
- `WorkspaceLayout`: Workspace layout snapshot (layout_id, created_at, monitors, windows).
- `ScreenCaptureResult`: In-memory screen capture payload.
- `ClipboardResult`: Clipboard operation payload with secret masking flag.
- `WindowOperationResult`: Result payload for focus/move/resize/snap/state actions.
- `DesktopSnapshot`: Aggregated desktop snapshot metadata without raw image bytes or clipboard text.

### 2. Window Controller (`app/automation/desktop/window_controller.py`)
- Reuses Phase 6.1 `WindowResolver` for window enumeration and process association.
- Operations:
  - `list_windows()`: Enumerates top-level visible desktop windows.
  - `get_active_window()`: Queries `win32gui.GetForegroundWindow()` for active foreground window.
  - `focus_window(hwnd)`: Restores minimized state and sets foreground focus (`SetForegroundWindow`).
  - `minimize_window(hwnd)`, `maximize_window(hwnd)`, `restore_window(hwnd)`.
  - `move_window(hwnd, x, y)`, `resize_window(hwnd, width, height)`.
  - `snap_window(hwnd, position)`: Snaps window to monitor work area (Left 50%, Right 50%, Top-Left, etc.).
  - `close_window(hwnd)`: Sends `WM_CLOSE` message (zero process termination).

### 3. Monitor Manager & Virtual Desktop (`app/automation/desktop/monitor_manager.py`, `virtual_desktop.py`)
- `MonitorManager`: Multi-monitor discovery via `win32api.EnumDisplayMonitors` and `GetMonitorInfo`. Identifies primary monitor, virtual screen bounds, work area (excluding taskbars), and window-to-monitor mapping.
- `VirtualDesktopManager`: Windows virtual desktop availability detection and active desktop querying with graceful fallback.

### 4. Workspace Manager (`app/automation/desktop/workspace_manager.py`)
- `capture_workspace_layout()`: Captures topology of active window positions, dimensions, states, and monitor assignments.
- `restore_workspace_layout(layout)`: Restores geometry for existing windows. Partial restore support (skips missing windows safely without launching apps or killing processes).

### 5. Screen Capturer (`app/automation/desktop/screen_capturer.py`)
- `ScreenCapturer`: High-performance local in-memory screen capture using `mss`:
  - `capture_all_monitors()`, `capture_monitor(monitor_id)`, `capture_region(x, y, width, height)`, `capture_window(hwnd)`.
  - Enforces in-memory retention policy: Screenshots are **never** saved to disk or uploaded automatically. Includes headless BitBlt fallback.

### 6. Clipboard Manager (`app/automation/desktop/clipboard_manager.py`)
- Safe Win32 clipboard operations (`win32clipboard`):
  - Reads and writes text, HTML, and file drop lists (`CF_HDROP`).
  - Enforces size limits (`max_text_chars`).
  - Integrates `SensitiveDataSanitizer` to mask secrets before returning clipboard data.
  - Does NOT store clipboard history or log clipboard text.
  - Preserves user clipboard state during CLI tests (`backup_clipboard()`, `restore_clipboard()`).

### 7. Desktop Controller Coordinator (`app/automation/desktop/desktop_controller.py`)
- `DesktopController`: Main desktop coordinator service uniting `WindowController`, `MonitorManager`, `VirtualDesktopManager`, `WorkspaceManager`, `ScreenCapturer`, and `ClipboardManager`. Provides `get_desktop_snapshot()`.

### 8. DI Integration & Configuration
- `AutomationDesktopSettings` added to `Settings` in `app/config/models.py`.
- Singletons registered in `ApplicationContainer` (`app/dependency/container.py`).
- Non-invasive bootstrapper initialization (IDLE state at startup, zero desktop actions).

### 9. CLI Diagnostic Suite (`main.py`)
- Added CLI commands: `--desktop-health-check`, `--window-control-test`, `--screenshot-test`, `--clipboard-test`, `--workspace-test`, `--monitor-test`, `--virtual-desktop-test`.

---

## Verification Summary

- **PyTest**: 14 passed / 14 total (100% pass rate).
- **Health Check CLI**: Returned `Status: HEALTHY`, `Win32 API: AVAILABLE`, `Window Control: AVAILABLE`, `Monitor Manager: AVAILABLE`, `Screen Capture: AVAILABLE`, `Clipboard: AVAILABLE`.
- **Ruff & Black**: Formatted and clean.
