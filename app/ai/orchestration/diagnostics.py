"""Diagnostic health and status provider for AI Orchestrator.

Phase 4.2 - AI Orchestrator & Reasoning Workflow Engine
"""

from typing import Any

from app.ai.orchestration.metrics import OrchestratorMetrics


class OrchestratorDiagnostics:
    """Provides diagnostic health reports and metric snapshots for AI Orchestrator."""

    def __init__(self, metrics: OrchestratorMetrics | None = None) -> None:
        self.metrics = metrics or OrchestratorMetrics()

    def get_health_report(
        self,
        state: str = "IDLE",
        enabled: bool = True,
        max_steps: int = 5,
        allow_tools: bool = True,
        registered_tools_count: int = 0,
        last_error: str | None = None,
    ) -> dict[str, Any]:
        """Format diagnostic health report dictionary."""
        metrics_snapshot = self.metrics.get_metrics_snapshot()
        status = "HEALTHY" if enabled and state != "FAILED" else "DEGRADED"

        return {
            "status": status,
            "subsystem": "AI Orchestrator & Reasoning Workflow Engine",
            "state": state,
            "enabled": enabled,
            "max_steps": max_steps,
            "allow_tools": allow_tools,
            "registered_tools_count": registered_tools_count,
            "last_error": last_error,
            "metrics": metrics_snapshot,
        }
