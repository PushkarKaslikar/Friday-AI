# Phase 6.4 Implementation Report — Application Control & Interaction Adapters Engine

## Subsystem Architecture Overview

Phase 6.4 introduces application-specific adapters for Friday AI Assistant, transforming generic Windows automation capabilities into reusable, structured application primitives for Windows File Explorer, Terminal family (CMD, PowerShell, Windows Terminal), and generic application launch and attach services. The subsystem resides in `app/automation/apps/`.

### Component Hierarchy

```
                    Application Request
                             |
                             v
                 ApplicationAdapterRegistry
                             |
         +-------------------+-------------------+
         |                   |                   |
         v                   v                   v
   ExplorerAdapter    TerminalAdapter    ApplicationLauncher
         |                   |                   |
         +-------------------+-------------------+
                             |
                             v
                 Existing Automation Layer
               ├── Phase 6.1 UIA Engine & ElementFinder
               ├── Phase 6.2 InputEngine
               ├── Phase 6.3 WindowController
               └── Phase 2 FilesystemService & PathSecurity
```

---

## Deliverables & Components

### 1. Exception Hierarchy & Domain Models (`app/automation/apps/errors.py`, `models.py`)
- `AppAdapterError`: Base exception for application adapter errors (`AppNotInstalledError`, `AppNotRunningError`, `AppAttachFailedError`, `AppLaunchFailedError`, `InvalidExecutableError`, `InvalidWorkingDirectoryError`, `ExplorerNavigationFailedError`, `TerminalNotAvailableError`).
- `ApplicationState`: Enum (`NOT_INSTALLED`, `INSTALLED`, `NOT_RUNNING`, `RUNNING`, `ATTACHED`, `LAUNCHING`, `READY`, `FAILED`).
- `ApplicationCapability`: Enum (`LAUNCH`, `ATTACH`, `FOCUS`, `NAVIGATION`, `ITEM_SELECTION`, `ITEM_OPEN`, `CREATE_FOLDER`, `INPUT`, `OUTPUT`, `WORKING_DIRECTORY`).
- `TerminalType`: Enum (`CMD`, `POWERSHELL`, `WINDOWS_TERMINAL`, `PWSH`).
- `ApplicationIdentity`: Structured identity (`app_id`, `display_name`, `executable_names`, `aliases`, `process_names`, `known_paths`, `capabilities`).
- `AttachedApplication`: Active process/window attachment object (`app_identity`, `process_id`, `hwnd`, `window_title`, `attached_at`, `state`, `capabilities`).
- `LaunchRequest`: Structured launch request (`application`, `executable`, `arguments`, `working_directory`, `environment_overrides`, `wait_for_ready`, `timeout`, `focus_after_launch`).
- `ApplicationLaunchResult`, `AdapterOperationResult`, `ExplorerOperationResult`, `TerminalOperationResult`, `TerminalOutput`.

### 2. Adapter Base & Registry (`app/automation/apps/base.py`, `registry.py`)
- `ApplicationAdapter`: Abstract base class specifying `identity`, `state`, `capabilities`, `is_installed()`, `is_running()`, `find_windows()`, `attach()`, `launch()`, `get_active_window()`, `health_check()`.
- `ApplicationAdapterRegistry`: Deterministic app_id and alias resolution service.

### 3. Application Launcher (`app/automation/apps/launcher.py`)
- `ApplicationLauncher`:
  - Executable resolution order: Explicit path -> Alias registry -> System `PATH` (`shutil.which`).
  - Executable extension & path validation (rejects raw `.js`, `.py`, `.bat`, `.txt` scripts without explicit interpreter).
  - Working directory validation via `PathSecurityManager.validate_path(path)` (returns `INVALID_WORKING_DIRECTORY` if non-existent or inaccessible; does NOT auto-create).
  - Spawns process cleanly via `subprocess.Popen(cmd_list, cwd=..., env=...)` with argument array (`shell=False`).
  - Bounded readiness strategy (`process_exists` -> `window_appears` -> `UIA_ready` -> `READY`).

### 4. File Explorer Adapter (`app/automation/apps/explorer_adapter.py`)
- `ExplorerAdapter`:
  - Launch & Attach: Finds top-level Explorer windows (`CabinetWClass`).
  - Navigation: `navigate_to(path)` validated with `PathSecurityManager`.
  - Location Query: `get_current_location()` using UIA address bar inspection.
  - Item Discovery & Selection: `list_items(max_items)`, `select_item(locator)`, `open_item(locator)` via Phase 6.1 UIA.
  - Directory Creation: `create_folder(folder_path)` using Phase 2 `FilesystemService` + `PathSecurityManager` (reusing Phase 2 filesystem safety!).

### 5. Terminal Adapter (`app/automation/apps/terminal_adapter.py`)
- `TerminalAdapter`:
  - Supports CMD (`cmd.exe`), PowerShell (`powershell.exe`/`pwsh.exe`), Windows Terminal (`wt.exe`).
  - Launch & Attach: Validates working directory with `PathSecurityManager`. Attaches to window by HWND/class.
  - Working Directory & Input: `set_working_directory(path)`, `type_command(command_text)` using Phase 6.2 `InputEngine` and Phase 6.1 UIA. Sanitizes secret tokens for log output.
  - Output Inspection: `read_output(max_chars)` reading UIA text buffer with `SensitiveDataSanitizer` masking and bounded output length. Reports availability honestly (`AVAILABLE`, `LIMITED`, `UNAVAILABLE`; NO OCR!).

### 6. Coordinator, Diagnostics & Infrastructure Wiring
- `ApplicationAdapterMetrics` (`app/automation/apps/metrics.py`) & `ApplicationAdapterDiagnostics` (`diagnostics.py`).
- `ApplicationAdapterManager` (`app/automation/apps/apps_controller.py`) main coordinator service.
- `AutomationAppsSettings` added under `AutomationSettings` in `app/config/models.py`.
- Singletons registered in `ApplicationContainer` (`app/dependency/container.py`).
- Non-invasive bootstrapper instantiation in IDLE state during startup step 5 in `app/bootstrap/bootstrapper.py`.

### 7. CLI Diagnostic Suite (`main.py`)
- Added CLI commands: `--application-adapter-health-check`, `--application-adapter-test`, `--app-launcher-test`, `--explorer-automation-test`, `--terminal-automation-test`.

---

## Verification Summary

- **PyTest**: 14 passed / 14 total (100% pass rate).
- **Health Check CLI**: Status `HEALTHY`, 2 registered adapters (`explorer`, `terminal`), CMD/PowerShell/WT available, Generic Launcher `READY`.
- **Ruff & Black**: Formatted and clean.
