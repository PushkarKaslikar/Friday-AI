"""Application Launcher service for safe, structured process launching and readiness verification."""

import os
import shutil
import subprocess
import time
from typing import Any, List, Optional

from app.automation.apps.errors import (
    InvalidExecutableError,
    InvalidWorkingDirectoryError,
)
from app.automation.apps.models import (
    ApplicationIdentity,
    ApplicationLaunchResult,
    ApplicationState,
    AttachedApplication,
    LaunchRequest,
)
from app.automation.desktop.window_controller import WindowController
from app.automation.uia.window_resolver import WindowResolver
from app.logging import logger

# Allowed binary executable extensions for Windows launcher
ALLOWED_EXECUTABLE_EXTENSIONS = {".exe", ".com"}

# Default launcher alias resolution map for standard Windows tools
DEFAULT_SYSTEM_ALIASES = {
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "windows explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "pwsh": "pwsh.exe",
    "terminal": "wt.exe",
    "windows terminal": "wt.exe",
    "wt": "wt.exe",
    "notepad": "notepad.exe",
    "calc": "calc.exe",
    "calculator": "calc.exe",
}


class ApplicationLauncher:
    """Service responsible for safe process launching, argument validation, and readiness verification."""

    def __init__(
        self,
        window_resolver: WindowResolver,
        window_controller: WindowController,
        path_security: Any | None = None,
    ) -> None:
        self.window_resolver = window_resolver
        self.window_controller = window_controller
        if path_security is None:
            from app.platform.filesystem.path_security import PathSecurityManager

            self.path_security = PathSecurityManager()
        else:
            self.path_security = path_security

    def resolve_executable(self, target: str, explicit_path: str | None = None) -> str:
        """Resolve executable path deterministically via explicit path, alias registry, or system PATH.

        Args:
            target: Application name, alias, or executable string.
            explicit_path: Optional explicit file path.

        Returns:
            Resolved absolute or PATH executable string.

        Raises:
            InvalidExecutableError: If executable cannot be resolved or is disallowed.
        """
        # 1. Check explicit path
        if explicit_path:
            norm_path = os.path.abspath(explicit_path)
            if not os.path.isfile(norm_path):
                raise InvalidExecutableError(
                    f"Explicit executable path '{explicit_path}' does not exist."
                )
            ext = os.path.splitext(norm_path)[1].lower()
            if ext not in ALLOWED_EXECUTABLE_EXTENSIONS:
                raise InvalidExecutableError(
                    f"Disallowed executable extension '{ext}' for '{explicit_path}'."
                )
            return norm_path

        clean_target = target.lower().strip()

        # 2. Check known system aliases
        alias_binary = DEFAULT_SYSTEM_ALIASES.get(clean_target)
        if alias_binary:
            found_path = shutil.which(alias_binary)
            if found_path:
                return found_path

        # 3. Check direct binary target via shutil.which
        found_target = shutil.which(target)
        if found_target:
            ext = os.path.splitext(found_target)[1].lower()
            if ext and ext not in ALLOWED_EXECUTABLE_EXTENSIONS and ext != ".bat":
                # Only allow standard binaries directly
                raise InvalidExecutableError(
                    f"Disallowed executable extension '{ext}' for '{target}'."
                )
            return found_target

        # 4. Check if target is absolute file path
        if os.path.isabs(target) and os.path.isfile(target):
            ext = os.path.splitext(target)[1].lower()
            if ext not in ALLOWED_EXECUTABLE_EXTENSIONS:
                raise InvalidExecutableError(
                    f"Disallowed executable extension '{ext}' for '{target}'."
                )
            return target

        raise InvalidExecutableError(
            f"Could not resolve executable for application target '{target}'."
        )

    def validate_working_directory(self, work_dir: str | None) -> str:
        """Validate working directory using PathSecurityManager without auto-creating missing paths.

        Args:
            work_dir: Target working directory string.

        Returns:
            Validated absolute path string.

        Raises:
            InvalidWorkingDirectoryError: If directory does not exist or is invalid.
        """
        if not work_dir:
            return os.getcwd()

        abs_dir = os.path.abspath(work_dir)
        if not os.path.exists(abs_dir) or not os.path.isdir(abs_dir):
            raise InvalidWorkingDirectoryError(
                f"Working directory '{work_dir}' does not exist."
            )

        # Check path security policy
        try:
            self.path_security.validate_path(abs_dir)
        except Exception as exc:
            raise InvalidWorkingDirectoryError(
                f"Working directory '{work_dir}' failed security validation: {exc}"
            )

        return abs_dir

    def launch(self, request: LaunchRequest) -> ApplicationLaunchResult:
        """Execute structured launch request, validate arguments, spawn process, and wait for readiness.

        Args:
            request: Structured LaunchRequest model.

        Returns:
            ApplicationLaunchResult object.
        """
        t0 = time.perf_counter()

        # 1. Resolve Executable
        try:
            exec_path = self.resolve_executable(request.application, request.executable)
        except InvalidExecutableError as exc:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return ApplicationLaunchResult(
                status="INVALID_EXECUTABLE",
                app_id=request.application,
                state=ApplicationState.FAILED,
                duration_ms=round(duration_ms, 2),
                reason=str(exc),
            )

        # 2. Validate Working Directory
        try:
            work_dir = self.validate_working_directory(request.working_directory)
        except InvalidWorkingDirectoryError as exc:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return ApplicationLaunchResult(
                status="INVALID_WORKING_DIRECTORY",
                app_id=request.application,
                state=ApplicationState.FAILED,
                duration_ms=round(duration_ms, 2),
                reason=str(exc),
            )

        # 3. Build Command List (No shell string execution!)
        cmd_list = [exec_path] + list(request.arguments)

        # Environment setup
        env = os.environ.copy()
        if request.environment_overrides:
            env.update(request.environment_overrides)

        logger.info(
            f"ApplicationLauncher: Launching '{exec_path}' with {len(request.arguments)} args in '{work_dir}'."
        )

        # 4. Spawn Process
        try:
            process = subprocess.Popen(
                cmd_list,
                cwd=work_dir,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=(
                    subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
                ),
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return ApplicationLaunchResult(
                status="FAILED",
                app_id=request.application,
                state=ApplicationState.FAILED,
                duration_ms=round(duration_ms, 2),
                reason=f"Failed to spawn process: {exc}",
            )

        pid = process.pid

        # 5. Process & Window Readiness Wait Loop
        resolved_hwnd = 0
        window_title = ""
        ready = False
        deadline = time.time() + request.timeout

        if not request.wait_for_ready:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return ApplicationLaunchResult(
                status="SUCCESS",
                app_id=request.application,
                process_id=pid,
                state=ApplicationState.RUNNING,
                duration_ms=round(duration_ms, 2),
                reason="Process spawned (wait_for_ready=False).",
            )

        while time.time() < deadline:
            # Check if process exited prematurely
            if process.poll() is not None and process.returncode != 0:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                return ApplicationLaunchResult(
                    status="FAILED",
                    app_id=request.application,
                    process_id=pid,
                    state=ApplicationState.FAILED,
                    duration_ms=round(duration_ms, 2),
                    reason=f"Process exited early with return code {process.returncode}.",
                )

            # Discover associated windows
            windows = self.window_resolver.enumerate_windows(include_hidden=False)
            matching_win = [
                w
                for w in windows
                if w.process_id == pid
                or os.path.basename(exec_path).lower() in w.process_name.lower()
            ]

            if matching_win:
                resolved_hwnd = matching_win[0].hwnd
                window_title = matching_win[0].title
                ready = True
                break

            time.sleep(0.15)

        duration_ms = (time.perf_counter() - t0) * 1000.0

        if not ready:
            return ApplicationLaunchResult(
                status="TIMEOUT",
                app_id=request.application,
                process_id=pid,
                state=ApplicationState.RUNNING,
                duration_ms=round(duration_ms, 2),
                reason=f"Process spawned but window readiness timed out after {request.timeout}s.",
            )

        # 6. Optional Focus
        if request.focus_after_launch and resolved_hwnd > 0:
            try:
                self.window_controller.focus_window(resolved_hwnd)
            except Exception:
                pass

        identity = ApplicationIdentity(
            app_id=request.application.lower(),
            display_name=request.application,
            executable_names=[os.path.basename(exec_path)],
            process_names=[os.path.basename(exec_path)],
        )

        attached_app = AttachedApplication(
            app_identity=identity,
            process_id=pid,
            hwnd=resolved_hwnd,
            window_title=window_title,
            state=ApplicationState.READY,
        )

        return ApplicationLaunchResult(
            status="SUCCESS",
            app_id=request.application,
            process_id=pid,
            hwnd=resolved_hwnd,
            state=ApplicationState.READY,
            duration_ms=round(duration_ms, 2),
            reason="Process launched and window readiness confirmed.",
            attached=attached_app,
        )
