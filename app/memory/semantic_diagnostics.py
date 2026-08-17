"""Diagnostic health reporter for Phase 5.5 Semantic Memory subsystem.

Phase 5.5 - Semantic Memory & Local Vector Index Foundation
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.memory.semantic_metrics import SemanticMemoryMetrics
    from app.memory.semantic_service import SemanticMemoryService


class SemanticMemoryDiagnostics:
    """Provides privacy-preserving health diagnostics and reports for Semantic Memory subsystem."""

    def __init__(
        self,
        service: "SemanticMemoryService",
        metrics: "SemanticMemoryMetrics",
    ) -> None:
        self._service = service
        self._metrics = metrics

    def get_health_report(self) -> dict:
        """Generate privacy-preserving health diagnostic report."""
        report = self._service.get_subsystem_report()
        consistency = self._service.validate_index_consistency()

        status = "HEALTHY"
        if not report.get("index_ready", False) or not report.get(
            "embedding_healthy", False
        ):
            status = "DEGRADED"
        if not consistency.is_consistent:
            status = "DEGRADED"

        return {
            "status": status,
            "embedding_provider": report.get(
                "embedding_provider", "LocalEmbeddingProvider"
            ),
            "embedding_model": report.get("embedding_model", "all-MiniLM-L6-v2"),
            "device": report.get("device", "CPU"),
            "dimensions": report.get("dimensions", 384),
            "faiss_index": (
                "READY" if report.get("index_ready", False) else "UNAVAILABLE"
            ),
            "indexed_memories": report.get("vector_count", 0),
            "sqlite_memories": consistency.sqlite_memory_count,
            "index_version": report.get("index_version", 1),
            "consistency": "PASS" if consistency.is_consistent else "FAIL",
            "search_status": (
                "AVAILABLE" if report.get("index_ready", False) else "UNAVAILABLE"
            ),
            "metrics": self._metrics.get_metrics_summary(),
        }
