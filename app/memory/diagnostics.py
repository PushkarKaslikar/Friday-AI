"""Diagnostics subsystem for Phase 5.1 Short-Term Memory.

Phase 5.1 - Short-Term Memory Foundation & Active Conversation Memory
"""

from typing import Any

from app.memory.metrics import MemoryMetrics
from app.memory.service import ShortTermMemoryService


class MemoryDiagnostics:
    """Diagnostic reporter for Short-Term Memory health status and runtime metrics."""

    def __init__(
        self,
        service: ShortTermMemoryService,
        metrics: MemoryMetrics | None = None,
    ) -> None:
        self.service = service
        self.metrics = metrics or MemoryMetrics()

    def get_health_report(self, session_id: str = "default_session") -> dict[str, Any]:
        """Generate a privacy-preserving health report of the Short-Term Memory subsystem."""
        try:
            container = self.service.store.get_session(session_id)
            active_session = container is not None
            current_entries = len(container.entries) if container else 0

            turns = self.service.get_recent_turns(session_id)
            entities = self.service.get_active_entities(session_id)
            task = self.service.get_current_task(session_id)
            pending = self.service.get_pending_request(session_id)

            snapshot = self.service.create_snapshot(session_id)

            return {
                "status": "HEALTHY",
                "active_session": active_session,
                "current_entries": current_entries,
                "current_turns": len(turns),
                "active_entities": len(entities),
                "current_task": "available" if task else "unavailable",
                "pending_clarification": pending is not None,
                "memory_usage": {
                    "snapshot_version": snapshot.version,
                    "entries_count": current_entries,
                    "max_entries": self.service.config.max_entries,
                    "max_context_characters": self.service.config.max_context_characters,
                    "max_tool_result_characters": self.service.config.max_tool_result_characters,
                },
                "max_entries": self.service.config.max_entries,
                "max_context_characters": self.service.config.max_context_characters,
                "metrics": self.metrics.get_metrics_summary(),
            }
        except Exception as err:  # noqa: BLE001
            return {
                "status": "DEGRADED",
                "active_session": False,
                "error": str(err),
                "metrics": self.metrics.get_metrics_summary(),
            }
