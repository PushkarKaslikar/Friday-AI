"""Diagnostic subsystem health reporter for Phase 6.5 Workflow Engine."""

import sys
from typing import Any

from app.automation.workflow.action_registry import WorkflowActionRegistry
from app.automation.workflow.engine import WorkflowEngine
from app.automation.workflow.metrics import WorkflowMetrics
from app.automation.workflow.verifier_registry import VerificationRegistry


class WorkflowDiagnostics:
    """Diagnostic reporter for Workflow Engine subsystem state and metrics."""

    def __init__(
        self,
        engine: WorkflowEngine | None = None,
        action_registry: WorkflowActionRegistry | None = None,
        verifier_registry: VerificationRegistry | None = None,
        metrics: WorkflowMetrics | None = None,
    ) -> None:
        self.engine = engine
        self.action_registry = action_registry or WorkflowActionRegistry()
        self.verifier_registry = verifier_registry or VerificationRegistry()
        self.metrics = metrics or WorkflowMetrics()

    def get_health_report(self) -> dict[str, Any]:
        """Generate structured health diagnostic report."""
        is_win32 = sys.platform == "win32"
        status = "HEALTHY" if is_win32 else "DEGRADED"

        active_wf = "NONE"
        if self.engine and self.engine._active_live_workflow_id:
            active_wf = self.engine._active_live_workflow_id

        registered_actions_count = len(self.action_registry._handlers)
        registered_verifiers_count = len(self.verifier_registry._evaluators)

        return {
            "status": status,
            "platform": sys.platform,
            "workflow_engine": "READY",
            "action_registry": f"{registered_actions_count} registered actions",
            "verifier_registry": f"{registered_verifiers_count} registered verifiers",
            "active_workflow": active_wf,
            "input_channel": "IDLE" if active_wf == "NONE" else "BUSY",
            "cancellation": "READY",
            "verification": "READY",
            "metrics": self.metrics.get_metrics_snapshot(),
        }
