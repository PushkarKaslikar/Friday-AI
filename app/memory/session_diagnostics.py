"""Diagnostics reporter for Phase 5.2 Session Memory Subsystem.

Phase 5.2 - Session Memory & Active Session Context Management
"""

from typing import Any

from app.memory.session_metrics import SessionMemoryMetrics
from app.memory.session_service import SessionMemoryService


class SessionMemoryDiagnostics:
    """Diagnostic reporter for Session Memory health status and aggregated runtime metrics."""

    def __init__(
        self,
        service: SessionMemoryService,
        metrics: SessionMemoryMetrics | None = None,
    ) -> None:
        self.service = service
        self.metrics = metrics or SessionMemoryMetrics()

    def get_health_report(self, session_id: str = "default_session") -> dict[str, Any]:
        """Generate a privacy-preserving health report of active session memory context."""
        try:
            ctx = self.service.get_session(session_id)
            active_session = ctx is not None
            task = self.service.get_current_task(session_id)
            topic = self.service.get_current_topic(session_id)
            snapshot = self.service.create_snapshot(session_id)

            return {
                "status": "HEALTHY",
                "active_session": active_session,
                "session_id": (
                    session_id[:8] + "..." if len(session_id) > 8 else session_id
                ),
                "session_status": ctx.status if ctx else "NO_SESSION",
                "turn_count": snapshot.turn_count,
                "current_task": "AVAILABLE" if task else "NONE",
                "current_topic": topic,
                "active_entities": len(snapshot.active_entities),
                "active_workflows": len(snapshot.recent_workflows),
                "pending_clarification": snapshot.pending_request is not None,
                "session_memory_entries": len(snapshot.active_entities)
                + snapshot.turn_count,
                "session_version": snapshot.version,
                "metrics": self.metrics.get_metrics_summary(),
            }
        except Exception as err:  # noqa: BLE001
            return {
                "status": "DEGRADED",
                "active_session": False,
                "error": str(err),
                "metrics": self.metrics.get_metrics_summary(),
            }
