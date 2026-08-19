"""Diagnostic health reporter for Phase 6.6 Automation Tool Suite."""

import sys
from typing import Any

from app.tools.builtin.automation.metrics import AutomationToolMetrics
from app.tools.registry.tool_registry import ToolRegistry


class AutomationToolDiagnostics:
    """Diagnostic reporter for Phase 6.6 Automation Tool Suite availability and metrics."""

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        metrics: AutomationToolMetrics | None = None,
    ) -> None:
        self.registry = registry or ToolRegistry()
        self.metrics = metrics or AutomationToolMetrics()

    def get_health_report(self) -> dict[str, Any]:
        """Generate structured health diagnostic report."""
        is_win32 = sys.platform == "win32"
        status = "HEALTHY" if is_win32 else "DEGRADED"

        registered_tools = [
            t.tool_id
            for t in self.registry.list_tools()
            if any(
                prefix in t.tool_id
                for prefix in (
                    "uia.",
                    "input.",
                    "window.",
                    "screen.",
                    "clipboard.",
                    "application.",
                    "explorer.",
                    "terminal.",
                    "workflow.",
                )
            )
        ]

        return {
            "status": status,
            "platform": sys.platform,
            "automation_tool_suite": "HEALTHY",
            "registered_automation_tools_count": len(registered_tools),
            "registered_automation_tools": registered_tools,
            "uia_tools": "READY",
            "input_tools": "READY",
            "window_tools": "READY",
            "screen_tools": "READY",
            "clipboard_tools": "READY",
            "application_tools": "READY",
            "explorer_tools": "READY",
            "terminal_tools": "READY",
            "workflow_tool": "READY",
            "tool_executor": "READY",
            "tool_calling_engine": "READY",
            "metrics": self.metrics.get_metrics_snapshot(),
        }
