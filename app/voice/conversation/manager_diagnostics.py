"""Diagnostic health and operational status provider for Conversation Manager.

Phase 3.8 - Conversation Manager, Session Context & Short-Term Memory
"""

from typing import Any

from app.voice.conversation.manager_metrics import ConversationManagerMetrics


class ConversationManagerDiagnostics:
    """Provides diagnostic health checks and metric snapshots for Conversation Manager."""

    def __init__(self, metrics: ConversationManagerMetrics | None = None) -> None:
        self.metrics = metrics or ConversationManagerMetrics()

    def get_health_report(
        self,
        service_state: str = "RUNNING",
        session_active: bool = False,
        session_id: str | None = None,
        turn_count: int = 0,
        context_turns: int = 0,
        active_entities_count: int = 0,
        pending_clarification: bool = False,
        context_size_chars: int = 0,
        context_limit_chars: int = 4000,
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
            "provider": "ConversationManager (Short-Term Memory)",
            "service_state": service_state,
            "session_active": session_active,
            "session_id": session_id,
            "turn_count": turn_count,
            "context_turns": context_turns,
            "active_entities_count": active_entities_count,
            "pending_clarification": pending_clarification,
            "context_size_chars": context_size_chars,
            "context_limit_chars": context_limit_chars,
            "enabled": enabled,
            "last_error": last_error,
            "metrics": metrics_snapshot,
        }
