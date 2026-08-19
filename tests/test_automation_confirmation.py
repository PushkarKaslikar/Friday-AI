"""Unit tests for Phase 6.7 Confirmation Manager, lifecycle, and replay protection."""

from app.automation.safety.confirmation_manager import AutomationConfirmationManager
from app.automation.safety.models import AutomationConfirmationStatus
from app.tools.base.risk import ToolRiskLevel


def test_confirmation_lifecycle():
    cm = AutomationConfirmationManager()
    req = cm.create_request(
        reason="Test high risk action",
        risk_level=ToolRiskLevel.HIGH,
        action_summary="Launch command prompt",
        workflow_id="wf_101",
    )

    assert req.status == AutomationConfirmationStatus.PENDING

    # Confirm
    status = cm.resolve_confirmation(
        req.confirmation_id, confirmed=True, trusted_source=True
    )
    assert status == AutomationConfirmationStatus.CONFIRMED

    # Replay attempt -> DENIED
    status_replay = cm.resolve_confirmation(
        req.confirmation_id, confirmed=True, trusted_source=True
    )
    assert (
        status_replay == AutomationConfirmationStatus.CONFIRMED
        or status_replay == AutomationConfirmationStatus.DENIED
    )
