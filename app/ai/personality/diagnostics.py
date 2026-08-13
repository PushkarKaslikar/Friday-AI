"""Diagnostic health and status provider for Personality Engine.

Phase 4.4 - Personality Engine & Behavioral Identity System
"""

from typing import Any

from app.ai.personality.metrics import PersonalityMetrics


class PersonalityDiagnostics:
    """Provides diagnostic health reports and metric snapshots for Personality Engine."""

    def __init__(self, metrics: PersonalityMetrics | None = None) -> None:
        self.metrics = metrics or PersonalityMetrics()

    def get_health_report(
        self,
        enabled: bool = True,
        identity_name: str = "Friday",
        formality: float = 0.5,
        humor: float = 0.25,
        active_modifiers_count: int = 0,
        rules_count: int = 20,
        last_error: str | None = None,
    ) -> dict[str, Any]:
        """Format diagnostic health report dictionary."""
        metrics_snapshot = self.metrics.get_metrics_snapshot()
        status = "HEALTHY" if enabled and not last_error else "DEGRADED"

        return {
            "status": status,
            "subsystem": "Personality Engine & Behavioral Identity System",
            "enabled": enabled,
            "identity_name": identity_name,
            "formality": formality,
            "humor": humor,
            "active_modifiers_count": active_modifiers_count,
            "behavioral_rules_count": rules_count,
            "last_error": last_error,
            "metrics": metrics_snapshot,
        }
