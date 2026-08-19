"""Action Registry mapping ActionType to service execution handlers."""

import time
from collections.abc import Callable

from app.automation.apps.apps_controller import ApplicationAdapterManager
from app.automation.apps.explorer_adapter import ExplorerAdapter
from app.automation.apps.terminal_adapter import TerminalAdapter
from app.automation.desktop.desktop_controller import DesktopController
from app.automation.input.input_engine import InputEngine
from app.automation.workflow.context import WorkflowExecutionContext
from app.automation.workflow.errors import UnsupportedActionError
from app.automation.workflow.models import (
    ActionResult,
    ActionType,
    WorkflowAction,
    WorkflowExecutionMode,
)
from app.logging import logger
from app.platform.filesystem.filesystem_service import FilesystemService


class WorkflowActionRegistry:
    """Registry mapping ActionType to handler methods routing execution to existing platform services."""

    def __init__(
        self,
        app_manager: ApplicationAdapterManager | None = None,
        desktop_controller: DesktopController | None = None,
        input_engine: InputEngine | None = None,
        filesystem_service: FilesystemService | None = None,
    ) -> None:
        self.app_manager = app_manager
        self.desktop_controller = desktop_controller
        self.input_engine = input_engine
        self.filesystem_service = filesystem_service
        self._handlers: dict[
            ActionType,
            Callable[
                [WorkflowAction, WorkflowExecutionContext, WorkflowExecutionMode],
                ActionResult,
            ],
        ] = {}
        self._register_default_handlers()

    def register_handler(
        self,
        action_type: ActionType,
        handler: Callable[
            [WorkflowAction, WorkflowExecutionContext, WorkflowExecutionMode],
            ActionResult,
        ],
    ) -> None:
        """Register a custom action handler."""
        self._handlers[action_type] = handler

    def has_handler(self, action_type: ActionType) -> bool:
        """Check if action handler is registered."""
        return action_type in self._handlers

    def execute_action(
        self,
        action: WorkflowAction,
        context: WorkflowExecutionContext,
        mode: WorkflowExecutionMode = WorkflowExecutionMode.SIMULATE,
    ) -> ActionResult:
        """Execute action in specified safety execution mode."""
        if action.action_type not in self._handlers:
            raise UnsupportedActionError(
                f"Action type '{action.action_type.value}' is not registered.",
                details={"action_type": action.action_type.value},
            )

        if mode == WorkflowExecutionMode.DRY_RUN:
            return ActionResult(
                status="SUCCESS",
                action_id=action.action_type.value,
                duration_ms=0.0,
                output={"mode": "DRY_RUN", "validated": True},
            )

        if mode == WorkflowExecutionMode.SIMULATE:
            return ActionResult(
                status="SUCCESS",
                action_id=action.action_type.value,
                duration_ms=1.0,
                output={"mode": "SIMULATE", "simulated": True, "target": action.target},
            )

        # LIVE Mode execution
        handler = self._handlers[action.action_type]
        t0 = time.perf_counter()
        try:
            res = handler(action, context, mode)
            res.duration_ms = (time.perf_counter() - t0) * 1000.0
            return res
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            logger.error(
                f"WorkflowActionRegistry: Action '{action.action_type.value}' failed: {exc}"
            )
            return ActionResult(
                status="FAILED",
                action_id=action.action_type.value,
                duration_ms=duration_ms,
                error=str(exc),
            )

    def _register_default_handlers(self) -> None:
        """Register built-in action handlers for all supported ActionTypes."""
        self._handlers[ActionType.LAUNCH_APP] = self._handle_launch_app
        self._handlers[ActionType.ATTACH_APP] = self._handle_attach_app
        self._handlers[ActionType.NAVIGATE_EXPLORER] = self._handle_navigate_explorer
        self._handlers[ActionType.SELECT_EXPLORER_ITEM] = (
            self._handle_select_explorer_item
        )
        self._handlers[ActionType.OPEN_EXPLORER_ITEM] = self._handle_open_explorer_item
        self._handlers[ActionType.CREATE_EXPLORER_FOLDER] = (
            self._handle_create_explorer_folder
        )
        self._handlers[ActionType.ATTACH_TERMINAL] = self._handle_attach_terminal
        self._handlers[ActionType.SET_TERMINAL_CWD] = self._handle_set_terminal_cwd
        self._handlers[ActionType.TYPE_TERMINAL_COMMAND] = (
            self._handle_type_terminal_command
        )
        self._handlers[ActionType.FOCUS_WINDOW] = self._handle_focus_window
        self._handlers[ActionType.MOVE_WINDOW] = self._handle_move_window
        self._handlers[ActionType.RESIZE_WINDOW] = self._handle_resize_window
        self._handlers[ActionType.SNAP_WINDOW] = self._handle_snap_window
        self._handlers[ActionType.MOUSE_CLICK] = self._handle_mouse_click
        self._handlers[ActionType.TYPE_TEXT] = self._handle_type_text
        self._handlers[ActionType.PRESS_HOTKEY] = self._handle_press_hotkey
        self._handlers[ActionType.FILESYSTEM_CREATE_FOLDER] = (
            self._handle_fs_create_folder
        )
        self._handlers[ActionType.FILESYSTEM_COPY_FILE] = self._handle_fs_copy_file
        self._handlers[ActionType.FILESYSTEM_MOVE_FILE] = self._handle_fs_move_file
        self._handlers[ActionType.CAPTURE_SCREEN] = self._handle_capture_screen
        self._handlers[ActionType.GET_WORKSPACE_SUMMARY] = (
            self._handle_get_workspace_summary
        )

    # Handlers routing to platform services:

    def _handle_launch_app(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        app_target = action.target or action.parameters.get("application", "")
        if self.app_manager:
            adapter = self.app_manager.resolve_adapter(app_target)
            if adapter:
                res = adapter.launch()
                if res and res.status in ("SUCCESS", "READY", "ATTACHED"):
                    if res.attached_app:
                        ctx.active_hwnd = res.attached_app.hwnd
                        ctx.active_app_id = res.attached_app.app_identity.app_id
                    return ActionResult(
                        status="SUCCESS",
                        action_id=action.action_type.value,
                        output=res.to_dict(),
                    )
                return ActionResult(
                    status="FAILED",
                    action_id=action.action_type.value,
                    error=res.error_message if res else "Launch failed",
                )
            launcher = self.app_manager.launcher
            res = launcher.launch_app(
                app_target, args=action.parameters.get("arguments")
            )
            return ActionResult(
                status="SUCCESS" if res.status in ("SUCCESS", "READY") else "FAILED",
                action_id=action.action_type.value,
                output=res.to_dict(),
            )
        return ActionResult(
            status="SUCCESS",
            action_id=action.action_type.value,
            output={"target": app_target},
        )

    def _handle_attach_app(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        app_target = action.target or action.parameters.get("application", "")
        if self.app_manager:
            adapter = self.app_manager.resolve_adapter(app_target)
            if adapter:
                res = adapter.attach()
                if res and res.state.value in ("ATTACHED", "READY"):
                    ctx.active_hwnd = res.hwnd
                    ctx.active_app_id = app_target
                    return ActionResult(
                        status="SUCCESS",
                        action_id=action.action_type.value,
                        output=res.to_dict(),
                    )
        return ActionResult(
            status="SUCCESS",
            action_id=action.action_type.value,
            output={"attached": app_target},
        )

    def _handle_navigate_explorer(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        path = action.target or action.parameters.get("path", "")
        if self.app_manager:
            exp_adapter: ExplorerAdapter | None = self.app_manager.get_adapter(
                "explorer"
            )
            if exp_adapter:
                res = exp_adapter.navigate_to(path)
                return ActionResult(
                    status="SUCCESS" if res.status == "SUCCESS" else "FAILED",
                    action_id=action.action_type.value,
                    error=res.message if res.status != "SUCCESS" else None,
                    output=res.to_dict(),
                )
        return ActionResult(
            status="SUCCESS", action_id=action.action_type.value, output={"path": path}
        )

    def _handle_select_explorer_item(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        item = action.target or action.parameters.get("item", "")
        if self.app_manager:
            exp_adapter: ExplorerAdapter | None = self.app_manager.get_adapter(
                "explorer"
            )
            if exp_adapter:
                res = exp_adapter.select_item(item)
                return ActionResult(
                    status="SUCCESS" if res.status == "SUCCESS" else "FAILED",
                    action_id=action.action_type.value,
                    output=res.to_dict(),
                )
        return ActionResult(
            status="SUCCESS",
            action_id=action.action_type.value,
            output={"selected": item},
        )

    def _handle_open_explorer_item(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        item = action.target or action.parameters.get("item", "")
        if self.app_manager:
            exp_adapter: ExplorerAdapter | None = self.app_manager.get_adapter(
                "explorer"
            )
            if exp_adapter:
                res = exp_adapter.open_item(item)
                return ActionResult(
                    status="SUCCESS" if res.status == "SUCCESS" else "FAILED",
                    action_id=action.action_type.value,
                    output=res.to_dict(),
                )
        return ActionResult(
            status="SUCCESS",
            action_id=action.action_type.value,
            output={"opened": item},
        )

    def _handle_create_explorer_folder(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        folder = action.target or action.parameters.get("folder", "")
        if self.app_manager:
            exp_adapter: ExplorerAdapter | None = self.app_manager.get_adapter(
                "explorer"
            )
            if exp_adapter:
                res = exp_adapter.create_folder(folder)
                return ActionResult(
                    status="SUCCESS" if res.status == "SUCCESS" else "FAILED",
                    action_id=action.action_type.value,
                    output=res.to_dict(),
                )
        return ActionResult(
            status="SUCCESS",
            action_id=action.action_type.value,
            output={"folder": folder},
        )

    def _handle_attach_terminal(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        term_target = action.target or action.parameters.get("terminal_type", "cmd")
        if self.app_manager:
            term_adapter: TerminalAdapter | None = self.app_manager.get_adapter(
                "terminal"
            )
            if term_adapter:
                res = term_adapter.attach()
                if res and res.state.value in ("ATTACHED", "READY"):
                    ctx.active_hwnd = res.hwnd
                    ctx.active_app_id = "terminal"
                    return ActionResult(
                        status="SUCCESS",
                        action_id=action.action_type.value,
                        output=res.to_dict(),
                    )
        return ActionResult(
            status="SUCCESS",
            action_id=action.action_type.value,
            output={"terminal": term_target},
        )

    def _handle_set_terminal_cwd(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        cwd = action.target or action.parameters.get("cwd", "")
        if self.app_manager:
            term_adapter: TerminalAdapter | None = self.app_manager.get_adapter(
                "terminal"
            )
            if term_adapter:
                res = term_adapter.set_working_directory(cwd)
                return ActionResult(
                    status="SUCCESS" if res.status == "SUCCESS" else "FAILED",
                    action_id=action.action_type.value,
                    output=res.to_dict(),
                )
        return ActionResult(
            status="SUCCESS", action_id=action.action_type.value, output={"cwd": cwd}
        )

    def _handle_type_terminal_command(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        cmd_text = action.parameters.get("command", "")
        if self.app_manager:
            term_adapter: TerminalAdapter | None = self.app_manager.get_adapter(
                "terminal"
            )
            if term_adapter:
                res = term_adapter.type_command(cmd_text)
                return ActionResult(
                    status="SUCCESS" if res.status == "SUCCESS" else "FAILED",
                    action_id=action.action_type.value,
                    output=res.to_dict(),
                )
        return ActionResult(
            status="SUCCESS", action_id=action.action_type.value, output={"typed": True}
        )

    def _handle_focus_window(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        target = action.target or ""
        if self.desktop_controller:
            res = self.desktop_controller.window_controller.focus_window(
                ctx.active_hwnd or 0
            )
            return ActionResult(
                status="SUCCESS" if res else "FAILED",
                action_id=action.action_type.value,
            )
        return ActionResult(
            status="SUCCESS",
            action_id=action.action_type.value,
            output={"focused": target},
        )

    def _handle_move_window(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        x = action.parameters.get("x", 0)
        y = action.parameters.get("y", 0)
        if self.desktop_controller and ctx.active_hwnd:
            res = self.desktop_controller.window_controller.move_window(
                ctx.active_hwnd, x, y
            )
            return ActionResult(
                status="SUCCESS" if res else "FAILED",
                action_id=action.action_type.value,
            )
        return ActionResult(
            status="SUCCESS",
            action_id=action.action_type.value,
            output={"x": x, "y": y},
        )

    def _handle_resize_window(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        w = action.parameters.get("width", 800)
        h = action.parameters.get("height", 600)
        if self.desktop_controller and ctx.active_hwnd:
            res = self.desktop_controller.window_controller.resize_window(
                ctx.active_hwnd, w, h
            )
            return ActionResult(
                status="SUCCESS" if res else "FAILED",
                action_id=action.action_type.value,
            )
        return ActionResult(
            status="SUCCESS",
            action_id=action.action_type.value,
            output={"width": w, "height": h},
        )

    def _handle_snap_window(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        pos = action.parameters.get("position", "left")
        if self.desktop_controller and ctx.active_hwnd:
            res = self.desktop_controller.window_controller.snap_window(
                ctx.active_hwnd, pos
            )
            return ActionResult(
                status="SUCCESS" if res else "FAILED",
                action_id=action.action_type.value,
            )
        return ActionResult(
            status="SUCCESS",
            action_id=action.action_type.value,
            output={"position": pos},
        )

    def _handle_mouse_click(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        x = action.parameters.get("x")
        y = action.parameters.get("y")
        if self.input_engine:
            res = self.input_engine.click(x=x, y=y)
            return ActionResult(
                status="SUCCESS" if res.is_success else "FAILED",
                action_id=action.action_type.value,
            )
        return ActionResult(
            status="SUCCESS",
            action_id=action.action_type.value,
            output={"clicked": True},
        )

    def _handle_type_text(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        text = action.parameters.get("text", "")
        if self.input_engine:
            res = self.input_engine.type_text(text)
            return ActionResult(
                status="SUCCESS" if res.is_success else "FAILED",
                action_id=action.action_type.value,
            )
        return ActionResult(
            status="SUCCESS", action_id=action.action_type.value, output={"typed": True}
        )

    def _handle_press_hotkey(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        keys = action.parameters.get("keys", [])
        if self.input_engine and keys:
            res = self.input_engine.hotkey(*keys)
            return ActionResult(
                status="SUCCESS" if res.is_success else "FAILED",
                action_id=action.action_type.value,
            )
        return ActionResult(
            status="SUCCESS",
            action_id=action.action_type.value,
            output={"hotkey": keys},
        )

    def _handle_fs_create_folder(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        folder = action.target or action.parameters.get("folder_path", "")
        if self.filesystem_service:
            res = self.filesystem_service.create_folder(folder)
            return ActionResult(
                status="SUCCESS" if res.get("created") else "FAILED",
                action_id=action.action_type.value,
                output=res,
            )
        return ActionResult(
            status="SUCCESS",
            action_id=action.action_type.value,
            output={"folder": folder},
        )

    def _handle_fs_copy_file(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        src = action.parameters.get("source", "")
        dest = action.parameters.get("destination", "")
        if self.filesystem_service:
            res = self.filesystem_service.copy_file(src, dest)
            return ActionResult(
                status="SUCCESS", action_id=action.action_type.value, output=res
            )
        return ActionResult(
            status="SUCCESS",
            action_id=action.action_type.value,
            output={"src": src, "dest": dest},
        )

    def _handle_fs_move_file(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        src = action.parameters.get("source", "")
        dest = action.parameters.get("destination", "")
        if self.filesystem_service:
            res = self.filesystem_service.move_item(src, dest)
            return ActionResult(
                status="SUCCESS", action_id=action.action_type.value, output=res
            )
        return ActionResult(
            status="SUCCESS",
            action_id=action.action_type.value,
            output={"src": src, "dest": dest},
        )

    def _handle_capture_screen(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        if self.desktop_controller:
            res = self.desktop_controller.screen_capturer.capture_screen()
            return ActionResult(
                status="SUCCESS" if res.status == "SUCCESS" else "FAILED",
                action_id=action.action_type.value,
                output=res.to_dict(),
            )
        return ActionResult(
            status="SUCCESS",
            action_id=action.action_type.value,
            output={"captured": True},
        )

    def _handle_get_workspace_summary(
        self,
        action: WorkflowAction,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> ActionResult:
        if self.desktop_controller:
            snap = self.desktop_controller.capture_desktop_snapshot()
            return ActionResult(
                status="SUCCESS",
                action_id=action.action_type.value,
                output=snap.to_dict(),
            )
        return ActionResult(
            status="SUCCESS",
            action_id=action.action_type.value,
            output={"summary": "desktop"},
        )
