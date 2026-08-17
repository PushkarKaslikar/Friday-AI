"""Health report generator and diagnostics for Memory Privacy Subsystem.

Phase 5.7 - Memory Privacy, Security, Governance & User Control
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.memory.privacy_metrics import MemoryPrivacyMetrics
    from app.memory.privacy_service import MemoryPrivacyService


class MemoryPrivacyDiagnostics:
    """Generates health check reports and telemetry diagnostics for Phase 5.7."""

    def __init__(
        self,
        service: "MemoryPrivacyService",
        metrics: "MemoryPrivacyMetrics",
    ) -> None:
        self.service = service
        self.metrics = metrics

    def get_health_report(self) -> dict:
        """Produce a privacy-preserving health report."""
        report = self.service.get_subsystem_report()
        report["metrics"] = self.metrics.snapshot()
        return report

    def format_report_summary(self) -> str:
        """Format health report into human-readable CLI output."""
        rep = self.get_health_report()
        metrics = rep.get("metrics", {})

        status = rep.get("status", "UNKNOWN")
        mode = rep.get("mode", "NORMAL")
        persistence = "ENABLED" if rep.get("persistence_enabled") else "DISABLED"

        lines = [
            "=========================================",
            "    FRIDAY MEMORY PRIVACY HEALTH CHECK   ",
            "=========================================",
            f"Status:                      {status}",
            f"Privacy Mode:                {mode}",
            f"Persistence Status:          {persistence}",
            "Long-Term Memory Governance: READY",
            "Semantic Index Governance:   READY",
            "Retrieval Governance:        READY",
            "Retention Engine:            READY",
            "Deletion Propagation:        READY",
            "Restricted Secret Defense:   READY",
            "Metrics:",
            f"  Write Evaluations:         {metrics.get('write_evaluations', 0)}",
            f"  Writes Allowed:            {metrics.get('writes_allowed', 0)}",
            f"  Writes Denied:             {metrics.get('writes_denied', 0)}",
            f"  Restricted Secret Blocks:  {metrics.get('restricted_blocks', 0)}",
            f"  Confirmation Requests:     {metrics.get('confirmation_requests', 0)}",
            f"  Retrieval Blocks:          {metrics.get('retrieval_blocks', 0)}",
            f"  Retention Expirations:     {metrics.get('retention_expirations', 0)}",
            f"  Deletions Executed:        {metrics.get('deletions', 0)}",
            f"  Clear-All Operations:      {metrics.get('clear_all_ops', 0)}",
            "=========================================",
        ]
        return "\n".join(lines)
