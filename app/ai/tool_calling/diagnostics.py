"""Diagnostic health and status provider for Tool Calling Engine.

Phase 4.3 - Tool Calling & Function Binding Engine
"""

from typing import Any

from app.ai.tool_calling.metrics import ToolCallingMetrics


class ToolCallingDiagnostics:
    """Provides diagnostic health reports and metric snapshots for Tool Calling Engine."""

    def __init__(self, metrics: ToolCallingMetrics | None = None) -> None:
        self.metrics = metrics or ToolCallingMetrics()

    def get_health_report(
        self,
        enabled: bool = True,
        max_tool_definitions: int = 20,
        max_result_chars: int = 4000,
        duplicate_call_protection: bool = True,
        schema_cache_enabled: bool = True,
        registered_tools_count: int = 0,
        last_error: str | None = None,
    ) -> dict[str, Any]:
        """Format diagnostic health report dictionary."""
        metrics_snapshot = self.metrics.get_metrics_snapshot()
        status = "HEALTHY" if enabled and not last_error else "DEGRADED"

        return {
            "status": status,
            "subsystem": "Tool Calling & Function Binding Engine",
            "enabled": enabled,
            "max_tool_definitions": max_tool_definitions,
            "max_result_chars": max_result_chars,
            "duplicate_call_protection": duplicate_call_protection,
            "schema_cache_enabled": schema_cache_enabled,
            "registered_tools_count": registered_tools_count,
            "last_error": last_error,
            "metrics": metrics_snapshot,
        }
