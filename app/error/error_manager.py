"""Centralized Error Manager for exception categorization, severity rating, and recovery execution."""

import threading
from collections.abc import Callable
from enum import Enum, auto
from typing import Any, Optional

from app.logging import logger
from app.services.events.event_bus import EventBus
from app.services.events.event_models import ServiceFailed


class ErrorSeverity(Enum):
    """Error severity rating levels."""

    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


class ErrorManager:
    """Centralized Error Manager categorizing exceptions and handling recovery strategies."""

    _instance: Optional["ErrorManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, event_bus: EventBus | None = None) -> None:
        if getattr(self, "_initialized", False):
            return

        self.event_bus = event_bus or EventBus()
        self._lock = threading.RLock()
        self._error_history: list[dict[str, Any]] = []
        self._recovery_strategies: dict[str, Callable[[Exception], bool]] = {}
        self._initialized = True

    def register_recovery_strategy(
        self, error_type_name: str, strategy: Callable[[Exception], bool]
    ) -> None:
        """Register a recovery callback for a specific exception class name."""
        with self._lock:
            self._recovery_strategies[error_type_name] = strategy

    def handle_error(
        self,
        exc: Exception,
        source: str = "unknown",
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    ) -> bool:
        """Categorize exception, record error, attempt recovery strategy, and notify EventBus.

        Args:
            exc: Exception instance.
            source: Source module or service name.
            severity: ErrorSeverity enum value.

        Returns:
            bool: True if error was recovered by registered strategy.
        """
        error_type = exc.__class__.__name__
        error_msg = str(exc)

        error_record = {
            "source": source,
            "type": error_type,
            "message": error_msg,
            "severity": severity.name,
        }

        with self._lock:
            self._error_history.append(error_record)

        if severity in (ErrorSeverity.HIGH, ErrorSeverity.CRITICAL):
            logger.error(
                f"ErrorManager [{severity.name}] from '{source}': {error_type} - {error_msg}"
            )
        else:
            logger.warning(
                f"ErrorManager [{severity.name}] from '{source}': {error_type} - {error_msg}"
            )

        # Attempt recovery strategy if registered
        recovered = False
        strategy = self._recovery_strategies.get(error_type)
        if strategy:
            try:
                recovered = strategy(exc)
                logger.info(
                    f"ErrorManager: Recovery strategy for '{error_type}' returned recovered={recovered}."
                )
            except Exception as strat_exc:  # noqa: BLE001
                logger.error(
                    f"ErrorManager: Recovery strategy for '{error_type}' failed: {strat_exc}"
                )

        if severity == ErrorSeverity.CRITICAL:
            self.event_bus.publish(
                ServiceFailed(service_name=source, error_message=error_msg)
            )

        return recovered

    def get_error_history(self) -> list[dict[str, Any]]:
        """Get copy of historical error logs."""
        with self._lock:
            return list(self._error_history)
