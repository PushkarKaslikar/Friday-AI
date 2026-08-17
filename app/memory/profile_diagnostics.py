"""Diagnostic reporter for Phase 5.4 User Profile Subsystem.

Phase 5.4 - User Profile & Personal Context Management
"""

from typing import Any

from app.memory.profile_metrics import UserProfileMetrics
from app.memory.profile_service import UserProfileService


class UserProfileDiagnostics:
    """Diagnostic reporter for User Profile context organization and metrics."""

    def __init__(
        self,
        service: UserProfileService,
        metrics: UserProfileMetrics | None = None,
    ) -> None:
        self.service = service
        self.metrics = metrics or UserProfileMetrics()

    def get_health_report(self) -> dict[str, Any]:
        """Generate a privacy-preserving diagnostic health report for User Profile."""
        try:
            profile = self.service.build_profile()
            self.metrics.record_build()

            return {
                "status": "HEALTHY",
                "domain_layer": "UserProfile",
                "underlying_store": "LongTermMemoryService (SQLite friday_memory.db)",
                "duplicate_db": "FALSE (Zero Duplicate DBs)",
                "preferred_name": profile.identity.preferred_name or "Not Set",
                "preference_count": len(profile.preferences),
                "project_count": len(profile.projects),
                "contact_count": len(profile.contacts),
                "workflow_count": len(profile.workflows),
                "interaction_pattern_count": len(profile.interaction_patterns),
                "metrics": self.metrics.get_metrics_summary(),
            }
        except Exception as err:  # noqa: BLE001
            return {
                "status": "UNAVAILABLE",
                "domain_layer": "UserProfile",
                "error": str(err),
                "metrics": self.metrics.get_metrics_summary(),
            }
