"""Diagnostic reporter for Phase 5.3 Long-Term Memory Subsystem.

Phase 5.3 - Long-Term Memory & Persistent Memory Foundation
"""

from typing import Any

from app.memory.db_manager import MemoryDatabaseManager
from app.memory.long_term_metrics import LongTermMemoryMetrics
from app.memory.long_term_service import LongTermMemoryService


class LongTermMemoryDiagnostics:
    """Diagnostic reporter for SQLite persistence health status and runtime metrics."""

    def __init__(
        self,
        db_manager: MemoryDatabaseManager,
        service: LongTermMemoryService,
        metrics: LongTermMemoryMetrics | None = None,
    ) -> None:
        self.db_manager = db_manager
        self.service = service
        self.metrics = metrics or LongTermMemoryMetrics()

    def get_health_report(self) -> dict[str, Any]:
        """Generate a privacy-preserving diagnostic health report for persistent long-term memory."""
        try:
            if not self.db_manager.is_initialized:
                self.db_manager.initialize_database()
            db_healthy = self.db_manager.is_healthy()
            count = self.service.repository.count(status="ACTIVE") if db_healthy else 0

            return {
                "status": "HEALTHY" if db_healthy else "UNAVAILABLE",
                "database": "SQLite",
                "persistence": "ENABLED",
                "semantic_search": "DISABLED (Phase 5.5/5.6)",
                "memory_count": count,
                "database_initialized": self.db_manager.is_initialized,
                "repository": "HEALTHY" if db_healthy else "DEGRADED",
                "promotion": "AVAILABLE",
                "metrics": self.metrics.get_metrics_summary(),
            }
        except Exception as err:  # noqa: BLE001
            return {
                "status": "UNAVAILABLE",
                "database": "SQLite",
                "persistence": "DISABLED",
                "error": str(err),
                "metrics": self.metrics.get_metrics_summary(),
            }
