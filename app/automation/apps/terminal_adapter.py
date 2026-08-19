"""Terminal Application Family Adapter (CMD, PowerShell, Windows Terminal)."""

import os
import shutil
import time
from typing import Any

from app.automation.apps.base import ApplicationAdapter
from app.automation.apps.errors import (
    AppAttachFailedError,
    AppNotRunningError,
)
from app.automation.apps.launcher import ApplicationLauncher
from app.automation.apps.models import (
    ApplicationCapability,
    ApplicationIdentity,
    ApplicationLaunchResult,
    ApplicationState,
    AttachedApplication,
    LaunchRequest,
    TerminalOperationResult,
    TerminalOutput,
    TerminalType,
)
from app.automation.desktop.models import DesktopWindow
from app.automation.desktop.window_controller import WindowController
from app.automation.input.input_engine import InputEngine
from app.automation.uia.element_finder import ElementFinder
from app.automation.uia.uia_engine import UIAutomationEngine
from app.automation.uia.window_resolver import WindowResolver
from app.logging import logger
from app.tools.execution.result_normalizer import SensitiveDataSanitizer

# Terminal Window Class Names
TERMINAL_WINDOW_CLASSES = {
    "ConsoleWindowClass",  # CMD / PowerShell classic console
    "CASCADIA_HOSTING_WINDOW_CLASS",  # Windows Terminal
    "PseudoConsoleWindow",
}


class TerminalAdapter(ApplicationAdapter):
    """Adapter for interacting with CMD, PowerShell, and Windows Terminal windows."""

    def __init__(
        self,
        window_resolver: WindowResolver,
        window_controller: WindowController,
        uia_engine: UIAutomationEngine,
        element_finder: ElementFinder,
        input_engine: InputEngine,
        launcher: ApplicationLauncher | None = None,
        path_security: Any | None = None,
    ) -> None:
        self.window_resolver = window_resolver
        self.window_controller = window_controller
        self.uia_engine = uia_engine
        self.element_finder = element_finder
        self.input_engine = input_engine
        self.launcher = launcher or ApplicationLauncher(
            window_resolver, window_controller
        )
        if path_security is None:
            from app.platform.filesystem.path_security import PathSecurityManager

            self.path_security = PathSecurityManager()
        else:
            self.path_security = path_security

        self._attached_app: AttachedApplication | None = None
        self._identity = ApplicationIdentity(
            app_id="terminal",
            display_name="Terminal Family",
            executable_names=["cmd.exe", "powershell.exe", "pwsh.exe", "wt.exe"],
            aliases=[
                "terminal",
                "cmd",
                "command prompt",
                "powershell",
                "pwsh",
                "windows terminal",
                "wt",
            ],
            process_names=[
                "cmd.exe",
                "powershell.exe",
                "pwsh.exe",
                "WindowsTerminal.exe",
                "wt.exe",
            ],
            capabilities={
                ApplicationCapability.LAUNCH,
                ApplicationCapability.ATTACH,
                ApplicationCapability.FOCUS,
                ApplicationCapability.INPUT,
                ApplicationCapability.OUTPUT,
                ApplicationCapability.WORKING_DIRECTORY,
            },
        )

    @property
    def identity(self) -> ApplicationIdentity:
        return self._identity

    @property
    def state(self) -> ApplicationState:
        if self._attached_app and self._attached_app.state == ApplicationState.ATTACHED:
            if self._attached_app.hwnd > 0 and self.window_resolver.is_window_valid(
                self._attached_app.hwnd
            ):
                return ApplicationState.ATTACHED
            self._attached_app = None
        if self.is_running():
            return ApplicationState.RUNNING
        if self.is_installed():
            return ApplicationState.INSTALLED
        return ApplicationState.NOT_INSTALLED

    def is_terminal_installed(self, term_type: TerminalType) -> bool:
        """Check availability of specific terminal binary."""
        binary_map = {
            TerminalType.CMD: "cmd.exe",
            TerminalType.POWERSHELL: "powershell.exe",
            TerminalType.PWSH: "pwsh.exe",
            TerminalType.WINDOWS_TERMINAL: "wt.exe",
        }
        binary = binary_map.get(term_type, "cmd.exe")
        return shutil.which(binary) is not None

    def is_installed(self) -> bool:
        return (
            self.is_terminal_installed(TerminalType.CMD)
            or self.is_terminal_installed(TerminalType.POWERSHELL)
            or self.is_terminal_installed(TerminalType.WINDOWS_TERMINAL)
        )

    def is_running(self) -> bool:
        return len(self.find_windows()) > 0

    def find_windows(self) -> list[DesktopWindow]:
        all_wins = self.window_controller.list_windows(include_hidden=False)
        term_wins = [
            w
            for w in all_wins
            if w.class_name in TERMINAL_WINDOW_CLASSES
            or any(
                proc in w.process_name.lower()
                for proc in ["cmd", "powershell", "pwsh", "windowsterminal", "wt"]
            )
        ]
        return term_wins

    def get_active_window(self) -> DesktopWindow | None:
        active = self.window_controller.get_active_window()
        if active and (
            active.class_name in TERMINAL_WINDOW_CLASSES
            or any(
                proc in active.process_name.lower()
                for proc in ["cmd", "powershell", "pwsh", "windowsterminal", "wt"]
            )
        ):
            return active
        return None

    def attach(self, hwnd: int | None = None) -> AttachedApplication:
        windows = self.find_windows()
        if not windows:
            raise AppNotRunningError("No active terminal windows found to attach.")

        target_win: DesktopWindow | None = None
        if hwnd and hwnd > 0:
            matching = [w for w in windows if w.hwnd == hwnd]
            if not matching:
                raise AppAttachFailedError(f"Terminal window HWND {hwnd} not found.")
            target_win = matching[0]
        else:
            active = self.get_active_window()
            target_win = active if active else windows[0]

        self._attached_app = AttachedApplication(
            app_identity=self.identity,
            process_id=target_win.process_id,
            hwnd=target_win.hwnd,
            window_title=target_win.title,
            state=ApplicationState.ATTACHED,
            capabilities=self.identity.capabilities,
        )

        logger.info(
            f"TerminalAdapter: Attached to terminal HWND {target_win.hwnd} ({target_win.title})."
        )
        return self._attached_app

    def launch_terminal(
        self,
        term_type: TerminalType = TerminalType.CMD,
        working_dir: str | None = None,
        arguments: list[str] | None = None,
    ) -> ApplicationLaunchResult:
        """Launch a specific terminal type (CMD, PowerShell, Windows Terminal).

        Args:
            term_type: Target TerminalType enum.
            working_dir: Optional working directory.
            arguments: Optional CLI arguments.

        Returns:
            ApplicationLaunchResult object.
        """
        if not self.is_terminal_installed(term_type):
            return ApplicationLaunchResult(
                status="NOT_INSTALLED",
                app_id=f"terminal_{term_type.value}",
                state=ApplicationState.NOT_INSTALLED,
                reason=f"Terminal type '{term_type.value}' is not installed on host OS.",
            )

        binary_map = {
            TerminalType.CMD: "cmd.exe",
            TerminalType.POWERSHELL: "powershell.exe",
            TerminalType.PWSH: "pwsh.exe",
            TerminalType.WINDOWS_TERMINAL: "wt.exe",
        }
        executable = binary_map.get(term_type, "cmd.exe")

        req = LaunchRequest(
            application=executable,
            executable=executable,
            arguments=arguments or [],
            working_directory=working_dir,
        )

        res = self.launcher.launch(req)
        if res.status == "SUCCESS" and res.attached:
            self._attached_app = res.attached
        return res

    def launch(self, request: LaunchRequest | None = None) -> ApplicationLaunchResult:
        if request is None:
            return self.launch_terminal(TerminalType.CMD)

        target_app = request.application.lower().strip()
        if "powershell" in target_app:
            term_type = TerminalType.POWERSHELL
        elif "terminal" in target_app or "wt" in target_app:
            term_type = TerminalType.WINDOWS_TERMINAL
        else:
            term_type = TerminalType.CMD

        return self.launch_terminal(
            term_type, request.working_directory, request.arguments
        )

    def set_working_directory(self, path: str) -> TerminalOperationResult:
        """Set working directory inside active terminal by sending cd / Set-Location command.

        Args:
            path: Target directory path string.

        Returns:
            TerminalOperationResult model.
        """
        # Validate path with PathSecurityManager
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
            return TerminalOperationResult(
                status="FAILED",
                message=f"Target working directory '{path}' does not exist.",
            )

        try:
            self.path_security.validate_path(abs_path)
        except Exception as exc:
            return TerminalOperationResult(
                status="FAILED",
                message=f"Path security validation failed: {exc}",
            )

        if not self._attached_app or not self.window_resolver.is_window_valid(
            self._attached_app.hwnd
        ):
            windows = self.find_windows()
            if windows:
                self.attach(windows[0].hwnd)
            else:
                return TerminalOperationResult(
                    status="NOT_RUNNING", message="No terminal window attached."
                )

        hwnd = self._attached_app.hwnd
        self.window_controller.focus_window(hwnd)

        # Detect terminal title to format cd command appropriately
        title = self._attached_app.window_title.lower()
        if "powershell" in title or "pwsh" in title:
            cd_cmd = f'Set-Location "{abs_path}"'
        else:
            cd_cmd = f'cd /d "{abs_path}"'

        return self.type_command(cd_cmd)

    def type_command(self, command_text: str) -> TerminalOperationResult:
        """Focus active terminal and type text via InputEngine / UIA text input.

        Args:
            command_text: Command string to type.

        Returns:
            TerminalOperationResult payload.
        """
        if not self._attached_app or not self.window_resolver.is_window_valid(
            self._attached_app.hwnd
        ):
            windows = self.find_windows()
            if windows:
                self.attach(windows[0].hwnd)
            else:
                return TerminalOperationResult(
                    status="NOT_RUNNING", message="No active terminal attached."
                )

        hwnd = self._attached_app.hwnd
        self.window_controller.focus_window(hwnd)

        # Sanitize sensitive credential patterns for log output
        sanitized_log = SensitiveDataSanitizer.sanitize_text(command_text)
        logger.info(
            f"TerminalAdapter: Typing command into HWND {hwnd}: '{sanitized_log}'"
        )

        try:
            # Type command and send ENTER key
            self.input_engine.type_text(command_text, delay_between_keys_ms=5.0)
            self.input_engine.press_key("enter")
            time.sleep(0.1)

            return TerminalOperationResult(
                status="SUCCESS",
                hwnd=hwnd,
                process_id=self._attached_app.process_id,
                message=f"Typed command into terminal HWND {hwnd}.",
            )
        except Exception as exc:
            return TerminalOperationResult(
                status="INPUT_FAILED",
                hwnd=hwnd,
                message=f"Failed to type command into terminal: {exc}",
            )

    def read_output(self, max_chars: int = 4096) -> TerminalOperationResult:
        """Inspect and read text output buffer from the attached terminal window via UIA text control.

        Args:
            max_chars: Maximum output characters to read.

        Returns:
            TerminalOperationResult object with TerminalOutput buffer if available.
        """
        if not self._attached_app or not self.window_resolver.is_window_valid(
            self._attached_app.hwnd
        ):
            windows = self.find_windows()
            if windows:
                self.attach(windows[0].hwnd)
            else:
                return TerminalOperationResult(
                    status="NOT_RUNNING",
                    output_available=False,
                    message="No active terminal attached to read output.",
                )

        hwnd = self._attached_app.hwnd
        output_text = ""
        output_captured = False

        try:
            root = self.uia_engine.get_root_element_for_hwnd(hwnd)
            if root:
                # Search for Text control or Edit control in terminal UIA tree
                text_elems = self.element_finder.find_all(root, control_type="Text")
                if not text_elems:
                    text_elems = self.element_finder.find_all(root, control_type="Edit")

                if text_elems:
                    combined = "\n".join([e.name for e in text_elems if e.name])
                    if combined:
                        output_text = (
                            combined[-max_chars:]
                            if len(combined) > max_chars
                            else combined
                        )
                        output_captured = True
        except Exception as exc:
            logger.debug(
                f"TerminalAdapter: Output buffer UIA inspection warning: {exc}"
            )

        # Sanitize captured text output before returning
        sanitized_output = SensitiveDataSanitizer.sanitize_text(output_text)

        term_out = TerminalOutput(
            terminal_type=TerminalType.CMD,
            process_id=self._attached_app.process_id,
            text=sanitized_output,
            is_complete=True,
            source="UIA_TEXT_BUFFER" if output_captured else "UNAVAILABLE",
        )

        return TerminalOperationResult(
            status="SUCCESS" if output_captured else "OUTPUT_UNAVAILABLE",
            hwnd=hwnd,
            process_id=self._attached_app.process_id,
            output=term_out,
            output_available=output_captured,
            message=(
                "Terminal UIA output buffer read successfully."
                if output_captured
                else "UIA output buffer not directly accessible on terminal window."
            ),
        )

    def health_check(self) -> dict[str, Any]:
        return {
            "app_id": self.identity.app_id,
            "installed": self.is_installed(),
            "cmd_installed": self.is_terminal_installed(TerminalType.CMD),
            "powershell_installed": self.is_terminal_installed(TerminalType.POWERSHELL),
            "windows_terminal_installed": self.is_terminal_installed(
                TerminalType.WINDOWS_TERMINAL
            ),
            "running": self.is_running(),
            "windows_count": len(self.find_windows()),
            "state": self.state.value,
        }
