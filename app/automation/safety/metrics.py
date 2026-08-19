"""Telemetry metrics counter tracker for Phase 6.7 Safety Governance."""

import threading
from typing import Any


class AutomationSafetyMetrics:
    """Thread-safe metric counter tracker for automation safety governance."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._evaluations = 0
        self._allowed = 0
        self._denied = 0
        self._confirmation_requested = 0
        self._confirmation_accepted = 0
        self._confirmation_denied = 0
        self._confirmation_expired = 0
        self._blast_radius_blocks = 0
        self._rate_limit_blocks = 0
        self._loop_protection_stops = 0
        self._failsafe_triggers = 0
        self._user_interruptions = 0
        self._kill_switch_triggers = 0
        self._lockdown_events = 0
        self._privacy_blocks = 0

    def increment_evaluations(self) -> None:
        with self._lock:
            self._evaluations += 1

    def increment_allowed(self) -> None:
        with self._lock:
            self._allowed += 1

    def increment_denied(self) -> None:
        with self._lock:
            self._denied += 1

    def increment_confirmation_requested(self) -> None:
        with self._lock:
            self._confirmation_requested += 1

    def increment_confirmation_accepted(self) -> None:
        with self._lock:
            self._confirmation_accepted += 1

    def increment_confirmation_denied(self) -> None:
        with self._lock:
            self._confirmation_denied += 1

    def increment_confirmation_expired(self) -> None:
        with self._lock:
            self._confirmation_expired += 1

    def increment_blast_radius_blocks(self) -> None:
        with self._lock:
            self._blast_radius_blocks += 1

    def increment_rate_limit_blocks(self) -> None:
        with self._lock:
            self._rate_limit_blocks += 1

    def increment_loop_protection_stops(self) -> None:
        with self._lock:
            self._loop_protection_stops += 1

    def increment_failsafe_triggers(self) -> None:
        with self._lock:
            self._failsafe_triggers += 1

    def increment_user_interruptions(self) -> None:
        with self._lock:
            self._user_interruptions += 1

    def increment_kill_switch_triggers(self) -> None:
        with self._lock:
            self._kill_switch_triggers += 1

    def increment_lockdown_events(self) -> None:
        with self._lock:
            self._lockdown_events += 1

    def increment_privacy_blocks(self) -> None:
        with self._lock:
            self._privacy_blocks += 1

    def get_metrics_snapshot(self) -> dict[str, Any]:
        """Return atomic snapshot dictionary of safety metrics counters."""
        with self._lock:
            return {
                "evaluations_count": self._evaluations,
                "allowed_count": self._allowed,
                "denied_count": self._denied,
                "confirmation_requested_count": self._confirmation_requested,
                "confirmation_accepted_count": self._confirmation_accepted,
                "confirmation_denied_count": self._confirmation_denied,
                "confirmation_expired_count": self._confirmation_expired,
                "blast_radius_blocks_count": self._blast_radius_blocks,
                "rate_limit_blocks_count": self._rate_limit_blocks,
                "loop_protection_stops_count": self._loop_protection_stops,
                "failsafe_triggers_count": self._failsafe_triggers,
                "user_interruptions_count": self._user_interruptions,
                "kill_switch_triggers_count": self._kill_switch_triggers,
                "lockdown_events_count": self._lockdown_events,
                "privacy_blocks_count": self._privacy_blocks,
            }
