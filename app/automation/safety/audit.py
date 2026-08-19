"""Bounded privacy-preserving audit log recorder for automation safety events."""

import collections
import threading

from app.automation.safety.models import (
    AutomationAuditEvent,
    AutomationConfirmationStatus,
    AutomationSafetyDecision,
    AutomationSafetyReasonCode,
)
from app.tools.base.risk import ToolRiskLevel


class AutomationAuditLog:
    """Thread-safe bounded in-memory audit log recorder enforcing data minimization."""

    def __init__(self, max_history_size: int = 500) -> None:
        self._lock = threading.Lock()
        self.max_history_size = max_history_size
        self._events: collections.deque[AutomationAuditEvent] = collections.deque(
            maxlen=max_history_size
        )

    def record_event(
        self,
        tool_name: str,
        risk_level: ToolRiskLevel,
        decision: AutomationSafetyDecision,
        reason_code: AutomationSafetyReasonCode,
        execution_status: str,
        workflow_id: str | None = None,
        action_type: str = "EXECUTE",
        confirmation_status: AutomationConfirmationStatus | None = None,
        duration_ms: float = 0.0,
        session_id: str = "session_main",
    ) -> AutomationAuditEvent:
        """Record a structured privacy-sanitized automation audit event."""
        event = AutomationAuditEvent(
            session_id=session_id,
            workflow_id=workflow_id,
            tool_name=tool_name,
            action_type=action_type,
            risk_level=risk_level,
            decision=decision,
            confirmation_status=confirmation_status,
            execution_status=execution_status,
            reason_code=reason_code,
            duration_ms=round(duration_ms, 2),
        )

        with self._lock:
            self._events.append(event)
            return event

    def get_events(self, limit: int = 100) -> list[AutomationAuditEvent]:
        """Return list of recent audit log events."""
        with self._lock:
            return list(self._events)[-limit:]

    def clear(self) -> None:
        """Clear audit history."""
        with self._lock:
            self._events.clear()
