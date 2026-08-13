"""Diagnostic health and operational status provider for Conversation State Machine.

Phase 3.7 - Conversation State Machine & Real-Time Voice Orchestration
"""

from typing import Any

from app.voice.conversation.metrics import ConversationMetrics


class ConversationDiagnostics:
    """Provides diagnostic health checks and metric snapshots for Conversation State Machine."""

    def __init__(self, metrics: ConversationMetrics | None = None) -> None:
        self.metrics = metrics or ConversationMetrics()

    def get_health_report(
        self,
        service_state: str = "RUNNING",
        current_state: str = "IDLE",
        session_active: bool = False,
        session_id: str | None = None,
        activation_source: str | None = None,
        turn_count: int = 0,
        barge_in_enabled: bool = True,
        session_timeout_seconds: float = 10.0,
        enabled: bool = True,
        last_error: str | None = None,
    ) -> dict[str, Any]:
        """Format comprehensive diagnostic health report dictionary."""
        metrics_snapshot = self.metrics.get_metrics_snapshot()
        status = "HEALTHY"
        if not enabled:
            status = "DISABLED"
        elif last_error:
            status = "DEGRADED"

        return {
            "status": status,
            "provider": "ConversationStateMachine (Deterministic)",
            "service_state": service_state,
            "current_state": current_state,
            "session_active": session_active,
            "session_id": session_id,
            "activation_source": activation_source,
            "turn_count": turn_count,
            "barge_in_enabled": barge_in_enabled,
            "session_timeout_seconds": session_timeout_seconds,
            "enabled": enabled,
            "last_error": last_error,
            "metrics": metrics_snapshot,
        }
