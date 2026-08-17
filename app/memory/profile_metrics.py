"""Metrics collector for Phase 5.4 User Profile & Personal Context Management.

Phase 5.4 - User Profile & Personal Context Management
"""

import threading
from typing import Any


class UserProfileMetrics:
    """Thread-safe metrics collector for User Profile domain queries and snapshot statistics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.profile_builds: int = 0
        self.snapshot_generations: int = 0
        self.preference_queries: int = 0
        self.project_queries: int = 0
        self.contact_queries: int = 0
        self.workflow_queries: int = 0
        self.profile_updates: int = 0

    def record_build(self) -> None:
        """Record a profile build event."""
        with self._lock:
            self.profile_builds += 1

    def record_snapshot(self) -> None:
        """Record a snapshot generation event."""
        with self._lock:
            self.snapshot_generations += 1

    def record_pref_query(self) -> None:
        """Record a preference lookup."""
        with self._lock:
            self.preference_queries += 1

    def record_project_query(self) -> None:
        """Record a project query."""
        with self._lock:
            self.project_queries += 1

    def record_contact_query(self) -> None:
        """Record a contact query."""
        with self._lock:
            self.contact_queries += 1

    def record_workflow_query(self) -> None:
        """Record a workflow query."""
        with self._lock:
            self.workflow_queries += 1

    def record_update(self) -> None:
        """Record a profile update operation."""
        with self._lock:
            self.profile_updates += 1

    def get_metrics_summary(self) -> dict[str, Any]:
        """Return aggregated user profile metrics dictionary."""
        with self._lock:
            return {
                "profile_builds": self.profile_builds,
                "snapshot_generations": self.snapshot_generations,
                "preference_queries": self.preference_queries,
                "project_queries": self.project_queries,
                "contact_queries": self.contact_queries,
                "workflow_queries": self.workflow_queries,
                "profile_updates": self.profile_updates,
            }
