"""Health report generator and diagnostics for Memory Retrieval Subsystem.

Phase 5.6 - Memory Retrieval & Relevant Context Engine
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.memory.retrieval_metrics import MemoryRetrievalMetrics
    from app.memory.retrieval_service import MemoryRetrievalService


class MemoryRetrievalDiagnostics:
    """Generates health check reports and telemetry diagnostics for Phase 5.6."""

    def __init__(
        self,
        service: "MemoryRetrievalService",
        metrics: "MemoryRetrievalMetrics",
    ) -> None:
        self.service = service
        self.metrics = metrics

    def get_health_report(self) -> dict:
        """Produce a comprehensive, privacy-preserving health report."""
        report = self.service.get_subsystem_report()
        report["metrics"] = self.metrics.snapshot()
        return report

    def format_report_summary(self) -> str:
        """Format health report into human-readable CLI output."""
        rep = self.get_health_report()
        metrics = rep.get("metrics", {})

        status = rep.get("status", "UNKNOWN")
        sem_status = (
            "AVAILABLE" if rep.get("semantic_service_available") else "UNAVAILABLE"
        )
        lt_status = (
            "AVAILABLE" if rep.get("long_term_service_available") else "UNAVAILABLE"
        )
        prof_status = (
            "AVAILABLE" if rep.get("user_profile_service_available") else "UNAVAILABLE"
        )
        sess_status = (
            "AVAILABLE" if rep.get("session_service_available") else "UNAVAILABLE"
        )

        lines = [
            "=========================================",
            "    FRIDAY MEMORY RETRIEVAL HEALTH CHECK ",
            "=========================================",
            f"Status:            {status}",
            f"Retrieval Policy:  READY ({rep.get('policy_mode', 'AUTO')})",
            f"Semantic Index:    {sem_status}",
            f"Long-Term Memory:  {lt_status}",
            f"User Profile:      {prof_status}",
            f"Session Memory:    {sess_status}",
            "Ranking Engine:    READY",
            "Context Builder:   READY",
            f"Max Results:       {rep.get('max_results', 5)}",
            f"Relevance Thresh:  {rep.get('relevance_threshold', 0.35)}",
            "Metrics:",
            f"  Requests:        {metrics.get('retrieval_requests', 0)}",
            f"  Triggered:       {metrics.get('retrieval_triggered', 0)}",
            f"  Skipped:         {metrics.get('retrieval_skipped', 0)}",
            f"  Memories Found:  {metrics.get('memories_selected', 0)}",
            f"  Degraded Runs:   {metrics.get('degraded_count', 0)}",
            f"  Avg Latency:     {metrics.get('average_latency_ms', 0.0)} ms",
            "=========================================",
        ]
        return "\n".join(lines)
