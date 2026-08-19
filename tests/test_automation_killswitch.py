"""Unit tests for Phase 6.7 Automation Kill Switch."""

from app.automation.safety.kill_switch import AutomationKillSwitch
from app.automation.safety.models import KillSwitchStatus


def test_kill_switch_trigger_and_reset():
    ks = AutomationKillSwitch()
    assert ks.status == KillSwitchStatus.ARMED
    assert not ks.is_triggered

    ks.trigger("Emergency user override")
    assert ks.is_triggered
    assert ks.status == KillSwitchStatus.TRIGGERED

    # Untrusted reset fails
    assert not ks.reset(trusted_user_confirmation=False)
    assert ks.is_triggered

    # Trusted reset succeeds
    assert ks.reset(trusted_user_confirmation=True)
    assert ks.status == KillSwitchStatus.ARMED
