"""Global Emergency Stop Kill Switch for Friday AI Assistant."""

import threading

from app.automation.safety.models import KillSwitchStatus
from app.logging import logger


class AutomationKillSwitch:
    """Thread-safe global emergency stop kill switch for computer automation."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._status = KillSwitchStatus.ARMED
        self._trigger_reason: str | None = None

    @property
    def status(self) -> KillSwitchStatus:
        with self._lock:
            return self._status

    @property
    def is_triggered(self) -> bool:
        with self._lock:
            return self._status == KillSwitchStatus.TRIGGERED

    @property
    def trigger_reason(self) -> str | None:
        with self._lock:
            return self._trigger_reason

    def trigger(
        self, reason: str = "Explicit emergency kill switch triggered"
    ) -> KillSwitchStatus:
        """Trigger emergency stop. Immediately halts new automation requests."""
        with self._lock:
            self._status = KillSwitchStatus.TRIGGERED
            self._trigger_reason = reason
            logger.warning(f"AutomationKillSwitch TRIGGERED: {reason}")
            return self._status

    def reset(self, trusted_user_confirmation: bool = False) -> bool:
        """Reset emergency stop. Requires explicit trusted user confirmation."""
        with self._lock:
            if not trusted_user_confirmation:
                logger.warning(
                    "AutomationKillSwitch reset rejected: Trusted user confirmation required."
                )
                return False

            self._status = KillSwitchStatus.RESETTING
            self._trigger_reason = None
            self._status = KillSwitchStatus.ARMED
            logger.info("AutomationKillSwitch successfully RESET to ARMED state.")
            return True
