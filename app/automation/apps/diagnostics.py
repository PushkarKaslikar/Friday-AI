"""Application Adapters Health Check Diagnostics Generator."""

import sys
from typing import Any

from app.automation.apps.explorer_adapter import ExplorerAdapter
from app.automation.apps.launcher import ApplicationLauncher
from app.automation.apps.models import TerminalType
from app.automation.apps.registry import ApplicationAdapterRegistry
from app.automation.apps.terminal_adapter import TerminalAdapter


class ApplicationAdapterDiagnostics:
    """Subsystem health reporter for Phase 6.4 Application Control & Interaction Adapters."""

    def __init__(
        self,
        registry: ApplicationAdapterRegistry,
        launcher: ApplicationLauncher,
        explorer_adapter: ExplorerAdapter,
        terminal_adapter: TerminalAdapter,
    ) -> None:
        self.registry = registry
        self.launcher = launcher
        self.explorer_adapter = explorer_adapter
        self.terminal_adapter = terminal_adapter

    def get_diagnostics_report(self) -> dict[str, Any]:
        """Perform non-invasive inspection report for Application Adapters subsystem.

        Does NOT launch processes, focus windows, or type commands during health check.

        Returns:
            Structured health report dictionary.
        """
        registered = self.registry.list_adapters()
        explorer_installed = self.explorer_adapter.is_installed()
        cmd_installed = self.terminal_adapter.is_terminal_installed(TerminalType.CMD)
        powershell_installed = self.terminal_adapter.is_terminal_installed(
            TerminalType.POWERSHELL
        )
        wt_installed = self.terminal_adapter.is_terminal_installed(
            TerminalType.WINDOWS_TERMINAL
        )

        status = "HEALTHY"
        if not explorer_installed or not cmd_installed:
            status = "DEGRADED"

        return {
            "status": status,
            "platform": sys.platform,
            "registered_adapters_count": len(registered),
            "registered_app_ids": [a.identity.app_id for a in registered],
            "generic_launcher": "READY",
            "explorer_adapter": "AVAILABLE" if explorer_installed else "UNAVAILABLE",
            "cmd_terminal": "AVAILABLE" if cmd_installed else "UNAVAILABLE",
            "powershell_terminal": (
                "AVAILABLE" if powershell_installed else "UNAVAILABLE"
            ),
            "windows_terminal": "AVAILABLE" if wt_installed else "UNAVAILABLE",
        }
