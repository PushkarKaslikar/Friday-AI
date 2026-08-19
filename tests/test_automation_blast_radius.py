"""Unit tests for Phase 6.7 Blast Radius limits evaluation."""

from app.automation.safety.models import AutomationBlastRadius
from app.automation.safety.policy import AutomationSafetyPolicy


def test_blast_radius_bounds():
    policy = AutomationSafetyPolicy(max_steps=5, max_blast_apps=2)

    good_blast = AutomationBlastRadius(step_count=3, app_count=1)
    ok, err = policy.evaluate_blast_radius(good_blast)
    assert ok
    assert err is None

    exceeded_blast = AutomationBlastRadius(step_count=10, app_count=1)
    ok_ex, err_ex = policy.evaluate_blast_radius(exceeded_blast)
    assert not ok_ex
    assert "Step count" in err_ex
