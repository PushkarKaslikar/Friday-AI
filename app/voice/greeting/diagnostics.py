"""Diagnostic health and operational status provider for Natural Greetings Foundation.

Phase 3.9 - Natural Greetings Foundation & Context-Aware Activation Responses
"""

from typing import Any

from app.voice.greeting.metrics import GreetingMetrics


class GreetingDiagnostics:
    """Provides diagnostic health checks and metric snapshots for Natural Greetings Subsystem."""

    def __init__(self, metrics: GreetingMetrics | None = None) -> None:
        self.metrics = metrics or GreetingMetrics()

    def get_health_report(
        self,
        service_state: str = "RUNNING",
        enabled: bool = True,
        provider_name: str = "TemplateGreetingProvider",
        context_aware: bool = True,
        recent_greeting_count: int = 0,
        max_history: int = 5,
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
            "provider": f"GreetingService ({provider_name})",
            "service_state": service_state,
            "enabled": enabled,
            "provider_name": provider_name,
            "context_aware": context_aware,
            "recent_greeting_count": recent_greeting_count,
            "max_history": max_history,
            "last_error": last_error,
            "metrics": metrics_snapshot,
        }
