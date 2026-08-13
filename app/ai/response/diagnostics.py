"""Diagnostic health and status provider for Response Generator.

Phase 4.5 - Dynamic Response Generation Engine
"""

from typing import Any

from app.ai.response.metrics import ResponseGenerationMetrics


class ResponseGenerationDiagnostics:
    """Provides diagnostic health reports and metric snapshots for Response Generator."""

    def __init__(self, metrics: ResponseGenerationMetrics | None = None) -> None:
        self.metrics = metrics or ResponseGenerationMetrics()

    def get_health_report(
        self,
        enabled: bool = True,
        max_response_chars: int = 2000,
        streaming_enabled: bool = True,
        llm_provider_ready: bool = True,
        last_error: str | None = None,
    ) -> dict[str, Any]:
        """Format diagnostic health report dictionary."""
        metrics_snapshot = self.metrics.get_metrics_snapshot()
        status = (
            "HEALTHY"
            if enabled and llm_provider_ready and not last_error
            else "DEGRADED"
        )

        return {
            "status": status,
            "subsystem": "Dynamic Response Generation Engine",
            "enabled": enabled,
            "max_response_chars": max_response_chars,
            "streaming_enabled": streaming_enabled,
            "llm_provider_ready": llm_provider_ready,
            "last_error": last_error,
            "metrics": metrics_snapshot,
        }
