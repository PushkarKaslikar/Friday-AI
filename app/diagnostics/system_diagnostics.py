"""System Diagnostics backend providing diagnostic datasets for system health inspection."""

from typing import Any

from app.logging import logger
from app.monitoring.performance_monitor import PerformanceMonitor
from app.services.base.service_interface import BaseService
from app.services.core.service_manager import ServiceManager
from app.tools.execution.tool_executor import ToolExecutor
from app.tools.registry.tool_registry import ToolRegistry


class SystemDiagnostics(BaseService):
    """Backend service aggregating process, service, thread, plugin, and tool diagnostics."""

    def __init__(
        self,
        performance_monitor: PerformanceMonitor | None = None,
        service_manager: ServiceManager | None = None,
        tool_registry: ToolRegistry | None = None,
        tool_executor: ToolExecutor | None = None,
    ) -> None:
        super().__init__(name="SystemDiagnostics", is_critical=False)
        self.performance_monitor = performance_monitor or PerformanceMonitor()
        self.service_manager = service_manager or ServiceManager()
        self.tool_registry = tool_registry or ToolRegistry()
        self.tool_executor = tool_executor

    def _do_initialize(self) -> None:
        """Initialize diagnostics resources."""
        logger.info("SystemDiagnostics initialized.")

    def _do_start(self) -> None:
        """Start diagnostics service."""
        logger.info("SystemDiagnostics started.")

    def _do_stop(self) -> None:
        """Stop diagnostics service."""
        logger.info("SystemDiagnostics stopped.")

    def generate_diagnostic_report(self) -> dict[str, Any]:
        """Generate comprehensive system diagnostics report dataset.

        Returns:
            dict: Complete snapshot containing performance metrics, service states, and tool status.
        """
        perf_metrics = self.performance_monitor.get_metrics()
        services_summary = self.service_manager.get_status_summary()

        registered_tools = self.tool_registry.registered_count
        enabled_tools = sum(1 for m in self.tool_registry.list_tools() if m.is_enabled)

        exec_metrics = (
            self.tool_executor.metrics.get_metrics_summary()
            if self.tool_executor
            else {}
        )
        active_execs = (
            self.tool_executor.tracker.active_count if self.tool_executor else 0
        )

        report = {
            "status": "HEALTHY",
            "performance": perf_metrics,
            "services_count": len(services_summary),
            "services": services_summary,
            "tool_engine": {
                "status": "HEALTHY",
                "registered_tools": registered_tools,
                "enabled_tools": enabled_tools,
                "active_executions": active_execs,
                "execution_metrics": exec_metrics,
            },
        }
        return report
