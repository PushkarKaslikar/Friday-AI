"""Windows File Explorer Application Adapter."""

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
    ExplorerOperationResult,
    LaunchRequest,
)
from app.automation.desktop.models import DesktopWindow
from app.automation.desktop.window_controller import WindowController
from app.automation.input.input_engine import InputEngine
from app.automation.uia.element_finder import ElementFinder
from app.automation.uia.uia_engine import UIAutomationEngine
from app.automation.uia.window_resolver import WindowResolver
from app.logging import logger

# Explorer Window Class Names
EXPLORER_WINDOW_CLASSES = {"CabinetWClass", "ExplorerWClass"}


class ExplorerAdapter(ApplicationAdapter):
    """Adapter for inspecting and controlling Windows File Explorer UI."""

    def __init__(
        self,
        window_resolver: WindowResolver,
        window_controller: WindowController,
        uia_engine: UIAutomationEngine,
        element_finder: ElementFinder,
        input_engine: InputEngine,
        filesystem_service: Any | None = None,
        launcher: ApplicationLauncher | None = None,
        path_security: Any | None = None,
    ) -> None:
        self.window_resolver = window_resolver
        self.window_controller = window_controller
        self.uia_engine = uia_engine
        self.element_finder = element_finder
        self.input_engine = input_engine
        if filesystem_service is None:
            from app.platform.filesystem.filesystem_service import FilesystemService

            self.filesystem_service = FilesystemService()
        else:
            self.filesystem_service = filesystem_service

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
            app_id="explorer",
            display_name="File Explorer",
            executable_names=["explorer.exe"],
            aliases=["explorer", "file explorer", "windows explorer"],
            process_names=["explorer.exe"],
            known_paths=["C:\\Windows\\explorer.exe"],
            capabilities={
                ApplicationCapability.LAUNCH,
                ApplicationCapability.ATTACH,
                ApplicationCapability.FOCUS,
                ApplicationCapability.NAVIGATION,
                ApplicationCapability.ITEM_SELECTION,
                ApplicationCapability.ITEM_OPEN,
                ApplicationCapability.CREATE_FOLDER,
            },
        )

    @property
    def identity(self) -> ApplicationIdentity:
        return self._identity

    @property
    def state(self) -> ApplicationState:
        if self._attached_app and self._attached_app.state == ApplicationState.ATTACHED:
            # Check if attached HWND is still valid
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

    def is_installed(self) -> bool:
        return shutil.which("explorer.exe") is not None or os.path.exists(
            "C:\\Windows\\explorer.exe"
        )

    def is_running(self) -> bool:
        windows = self.find_windows()
        return len(windows) > 0

    def find_windows(self) -> list[DesktopWindow]:
        all_windows = self.window_controller.list_windows(include_hidden=False)
        explorer_wins = [
            w
            for w in all_windows
            if w.class_name in EXPLORER_WINDOW_CLASSES
            or "explorer" in w.process_name.lower()
        ]
        return explorer_wins

    def get_active_window(self) -> DesktopWindow | None:
        active = self.window_controller.get_active_window()
        if active and (
            active.class_name in EXPLORER_WINDOW_CLASSES
            or "explorer" in active.process_name.lower()
        ):
            return active
        return None

    def attach(self, hwnd: int | None = None) -> AttachedApplication:
        windows = self.find_windows()
        if not windows:
            raise AppNotRunningError(
                "No running File Explorer windows found to attach."
            )

        target_win: DesktopWindow | None = None
        if hwnd and hwnd > 0:
            matching = [w for w in windows if w.hwnd == hwnd]
            if not matching:
                raise AppAttachFailedError(f"Explorer window HWND {hwnd} not found.")
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
            f"ExplorerAdapter: Attached to Explorer HWND {target_win.hwnd} ({target_win.title})."
        )
        return self._attached_app

    def launch(self, request: LaunchRequest | None = None) -> ApplicationLaunchResult:
        if request is None:
            request = LaunchRequest(application="explorer")

        res = self.launcher.launch(request)
        if res.status == "SUCCESS" and res.attached:
            self._attached_app = res.attached
        return res

    def navigate_to(self, target_path: str) -> ExplorerOperationResult:
        """Navigate File Explorer UI to the specified directory path.

        Args:
            target_path: Target directory path string.

        Returns:
            ExplorerOperationResult object.
        """
        # Validate path using PathSecurityManager
        abs_path = os.path.abspath(target_path)
        if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
            return ExplorerOperationResult(
                status="NAVIGATION_FAILED",
                target_path=target_path,
                message=f"Target directory '{target_path}' does not exist or is not a directory.",
            )

        try:
            self.path_security.validate_path(abs_path)
        except Exception as exc:
            return ExplorerOperationResult(
                status="NAVIGATION_FAILED",
                target_path=target_path,
                message=f"Path security check failed: {exc}",
            )

        # Attach or launch Explorer if not attached
        if not self._attached_app or not self.window_resolver.is_window_valid(
            self._attached_app.hwnd
        ):
            windows = self.find_windows()
            if windows:
                self.attach(windows[0].hwnd)
            else:
                launch_res = self.launch(
                    LaunchRequest(application="explorer", arguments=[abs_path])
                )
                if launch_res.status != "SUCCESS":
                    return ExplorerOperationResult(
                        status="NAVIGATION_FAILED",
                        target_path=abs_path,
                        message=f"Failed to launch Explorer: {launch_res.reason}",
                    )
                return ExplorerOperationResult(
                    status="SUCCESS",
                    target_path=abs_path,
                    current_path=abs_path,
                    hwnd=launch_res.hwnd,
                    message="Explorer launched directly at target directory.",
                )

        # If attached, focus window and navigate
        hwnd = self._attached_app.hwnd
        self.window_controller.focus_window(hwnd)

        # Try launching explorer at path to update/open window
        try:
            shutil.os.system(f'explorer.exe "{abs_path}"')
            time.sleep(0.3)
            return ExplorerOperationResult(
                status="SUCCESS",
                target_path=abs_path,
                current_path=abs_path,
                hwnd=hwnd,
                window_title=self._attached_app.window_title,
                message=f"Navigated Explorer window to '{abs_path}'.",
            )
        except Exception as exc:
            return ExplorerOperationResult(
                status="NAVIGATION_FAILED",
                target_path=abs_path,
                message=f"Failed to execute navigation: {exc}",
            )

    def get_current_location(self) -> ExplorerOperationResult:
        """Inspect active/attached File Explorer window for current location path."""
        if not self._attached_app or not self.window_resolver.is_window_valid(
            self._attached_app.hwnd
        ):
            windows = self.find_windows()
            if windows:
                self.attach(windows[0].hwnd)
            else:
                return ExplorerOperationResult(
                    status="NOT_RUNNING",
                    message="No active File Explorer window attached or running.",
                )

        hwnd = self._attached_app.hwnd
        win = self.window_controller.list_windows()
        matching = [w for w in win if w.hwnd == hwnd]
        title = matching[0].title if matching else self._attached_app.window_title

        return ExplorerOperationResult(
            status="SUCCESS",
            current_path=title,
            window_title=title,
            hwnd=hwnd,
            message="Retrieved Explorer window location title.",
        )

    def list_items(self, max_items: int = 100) -> ExplorerOperationResult:
        """Inspect visible folder item names inside the attached Explorer folder view bounded by max_items."""
        if not self._attached_app or not self.window_resolver.is_window_valid(
            self._attached_app.hwnd
        ):
            windows = self.find_windows()
            if windows:
                self.attach(windows[0].hwnd)
            else:
                return ExplorerOperationResult(
                    status="NOT_RUNNING",
                    message="No active File Explorer window attached.",
                )

        hwnd = self._attached_app.hwnd
        visible_names: list[str] = []

        try:
            root = self.uia_engine.get_root_element_for_hwnd(hwnd)
            if root:
                # Find List or DataGrid items
                items = self.element_finder.find_all(root, control_type="ListItem")
                for item in items[:max_items]:
                    if item.name:
                        visible_names.append(item.name)
        except Exception as exc:
            logger.debug(
                f"ExplorerAdapter: UIA item discovery encountered warning: {exc}"
            )

        return ExplorerOperationResult(
            status="SUCCESS",
            hwnd=hwnd,
            visible_items=visible_names,
            message=f"Discovered {len(visible_names)} visible items in Explorer view.",
        )

    def select_item(self, item_name: str) -> ExplorerOperationResult:
        """Find and select/focus a file or folder item by name inside Explorer view."""
        if not self._attached_app or not self.window_resolver.is_window_valid(
            self._attached_app.hwnd
        ):
            return ExplorerOperationResult(
                status="NOT_RUNNING", message="No active Explorer window attached."
            )

        hwnd = self._attached_app.hwnd
        try:
            root = self.uia_engine.get_root_element_for_hwnd(hwnd)
            if root:
                elem = self.element_finder.find_first(root, name=item_name)
                if elem:
                    elem.set_focus()
                    return ExplorerOperationResult(
                        status="SUCCESS",
                        hwnd=hwnd,
                        selected_items=[item_name],
                        message=f"Selected item '{item_name}' in Explorer.",
                    )
        except Exception as exc:
            logger.debug(f"ExplorerAdapter: Select item UIA fallback: {exc}")

        return ExplorerOperationResult(
            status="ITEM_NOT_FOUND",
            hwnd=hwnd,
            message=f"Could not find or select item '{item_name}' in Explorer view.",
        )

    def open_item(self, item_name: str) -> ExplorerOperationResult:
        """Find and open/invoke a file or folder item by name inside Explorer view."""
        select_res = self.select_item(item_name)
        if select_res.status != "SUCCESS":
            return select_res

        # Press Enter key to open item
        try:
            self.input_engine.press_key("enter")
            return ExplorerOperationResult(
                status="SUCCESS",
                hwnd=self._attached_app.hwnd,
                selected_items=[item_name],
                message=f"Opened item '{item_name}' in Explorer.",
            )
        except Exception as exc:
            return ExplorerOperationResult(
                status="FAILED",
                message=f"Failed to open item '{item_name}': {exc}",
            )

    def create_folder(self, folder_path: str) -> ExplorerOperationResult:
        """Create a directory on disk using Phase 2 FilesystemService + PathSecurityManager."""
        try:
            res = self.filesystem_service.create_folder(folder_path)
            if isinstance(res, dict) and res.get("created"):
                return ExplorerOperationResult(
                    status="SUCCESS",
                    current_path=folder_path,
                    target_path=folder_path,
                    message=f"Folder '{folder_path}' created successfully via FilesystemService.",
                )
            return ExplorerOperationResult(
                status="FAILED",
                target_path=folder_path,
                message=f"FilesystemService failed to create directory: {res}",
            )
        except Exception as exc:
            return ExplorerOperationResult(
                status="FAILED",
                target_path=folder_path,
                message=f"Directory creation error: {exc}",
            )

    def health_check(self) -> dict[str, Any]:
        return {
            "app_id": self.identity.app_id,
            "installed": self.is_installed(),
            "running": self.is_running(),
            "windows_count": len(self.find_windows()),
            "state": self.state.value,
        }
