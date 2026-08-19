"""Unit tests for Phase 6.7 Automation Audit Log."""

from app.automation.safety.audit import AutomationAuditLog
from app.automation.safety.models import (
    AutomationSafetyDecision,
    AutomationSafetyReasonCode,
)
from app.tools.base.risk import ToolRiskLevel


def test_audit_log_record_and_bounded_size():
    audit = AutomationAuditLog(max_history_size=10)

    for i in range(15):
        audit.record_event(
            tool_name=f"tool_{i}",
            risk_level=ToolRiskLevel.LOW,
            decision=AutomationSafetyDecision.ALLOW,
            reason_code=AutomationSafetyReasonCode.ALLOW,
            execution_status="SUCCESS",
        )

    events = audit.get_events(limit=100)
    assert len(events) == 10
    assert events[-1].tool_name == "tool_14"
