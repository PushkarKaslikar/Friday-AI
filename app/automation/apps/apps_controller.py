"""Main Application Adapter Coordinator Service (ApplicationAdapterManager)."""

from typing import Any

from app.automation.apps.base import ApplicationAdapter
from app.automation.apps.diagnostics import ApplicationAdapterDiagnostics
from app.automation.apps.explorer_adapter import ExplorerAdapter
from app.automation.apps.launcher import ApplicationLauncher
from app.automation.apps.metrics import ApplicationAdapterMetrics
from app.automation.apps.models import (
    ApplicationLaunchResult,
    AttachedApplication,
    LaunchRequest,
)
from app.automation.apps.registry import ApplicationAdapterRegistry
from app.automation.apps.terminal_adapter import TerminalAdapter
from app.logging import logger


class ApplicationAdapterManager:
    """Coordinator service for Phase 6.4 Application Control & Interaction Adapters."""

    def __init__(
        self,
        registry: ApplicationAdapterRegistry,
        launcher: ApplicationLauncher,
        explorer_adapter: ExplorerAdapter,
        terminal_adapter: TerminalAdapter,
        metrics: ApplicationAdapterMetrics | None = None,
        diagnostics: ApplicationAdapterDiagnostics | None = None,
    ) -> None:
        self.registry = registry
        self.launcher = launcher
        self.explorer_adapter = explorer_adapter
        self.terminal_adapter = terminal_adapter
        self.metrics = metrics or ApplicationAdapterMetrics()
        self.diagnostics = diagnostics or ApplicationAdapterDiagnostics(
            registry=registry,
            launcher=launcher,
            explorer_adapter=explorer_adapter,
            terminal_adapter=terminal_adapter,
        )

        # Auto-register core adapters into registry if not already registered
        self._initialize_default_adapters()

    def _initialize_default_adapters(self) -> None:
        """Register default Explorer and Terminal adapters."""
        try:
            if not self.registry.is_adapter_registered("explorer"):
                self.registry.register_adapter(self.explorer_adapter)
            if not self.registry.is_adapter_registered("terminal"):
                self.registry.register_adapter(self.terminal_adapter)
        except ValueError as exc:
            logger.debug(
                f"ApplicationAdapterManager: Default adapter registration note: {exc}"
            )

    def resolve_adapter(self, alias_or_id: str) -> ApplicationAdapter | None:
        """Resolve a registered application adapter by name, app_id, or alias."""
        adapter = self.registry.get_adapter(alias_or_id)
        status = "SUCCESS" if adapter else "NOT_FOUND"
        self.metrics.record_operation("resolution", "resolve_adapter", status, 0.1)
        return adapter

    def launch_application(self, request: LaunchRequest) -> ApplicationLaunchResult:
        """Resolve adapter if present or use generic launcher to spawn process."""
        adapter = self.resolve_adapter(request.application)
        if adapter:
            res = adapter.launch(request)
        else:
            res = self.launcher.launch(request)

        self.metrics.record_operation(
            "launch", "launch_application", res.status, res.duration_ms
        )
        return res

    def attach_application(
        self, alias_or_id: str, hwnd: int | None = None
    ) -> AttachedApplication:
        """Attach to a running application by name, app_id, or HWND."""
        adapter = self.resolve_adapter(alias_or_id)
        if adapter:
            attached = adapter.attach(hwnd)
            self.metrics.record_operation(
                "attach", "attach_application", "SUCCESS", 0.5
            )
            return attached

        # Fallback for generic running process
        windows = self.launcher.window_controller.list_windows()
        matching = [
            w
            for w in windows
            if alias_or_id.lower() in w.title.lower()
            or alias_or_id.lower() in w.process_name.lower()
        ]
        if not matching:
            raise ValueError(
                f"No running window found matching application target '{alias_or_id}'."
            )

        target_win = matching[0]
        self.metrics.record_operation("attach", "attach_application", "SUCCESS", 0.5)
        return AttachedApplication(
            app_identity=self.explorer_adapter.identity,  # fallback identity
            process_id=target_win.process_id,
            hwnd=target_win.hwnd,
            window_title=target_win.title,
        )

    def list_registered_adapters(self) -> list[ApplicationAdapter]:
        """List all currently registered application adapters."""
        return self.registry.list_adapters()

    def get_health_report(self) -> dict[str, Any]:
        """Return aggregated subsystem health check report."""
        return self.diagnostics.get_diagnostics_report()
