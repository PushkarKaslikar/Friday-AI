"""Unit tests for Phase 6.7 Automation Safety Policy and Safety Analyzer."""

from app.automation.safety.analyzer import AutomationSafetyAnalyzer
from app.automation.safety.models import AutomationSafetyDecision, AutomationSafetyMode
from app.automation.safety.policy import AutomationSafetyPolicy
from app.tools.base.risk import ToolRiskLevel
from app.tools.builtin.automation.uia_tools import UiaListWindowsTool
from app.tools.registry.tool_registry import ToolRegistry


def test_safety_policy_evaluation():
    policy = AutomationSafetyPolicy()

    # LOW risk tool -> ALLOW
    res1 = policy.evaluate_tool_risk("uia.list_windows", ToolRiskLevel.LOW)
    assert res1.decision == AutomationSafetyDecision.ALLOW

    # HIGH risk tool -> REQUIRE_CONFIRMATION
    res2 = policy.evaluate_tool_risk("workflow.execute_sequence", ToolRiskLevel.HIGH)
    assert res2.decision == AutomationSafetyDecision.REQUIRE_CONFIRMATION

    # Lockdown mode -> AUTOMATION_DISABLED
    policy.mode = AutomationSafetyMode.LOCKDOWN
    res3 = policy.evaluate_tool_risk("uia.list_windows", ToolRiskLevel.LOW)
    assert res3.decision == AutomationSafetyDecision.AUTOMATION_DISABLED


def test_safety_analyzer_workflow_inspection():
    registry = ToolRegistry()
    registry.register_tool(UiaListWindowsTool())
    analyzer = AutomationSafetyAnalyzer(tool_registry=registry)

    plan = {
        "workflow_id": "wf_test_001",
        "steps": [
            {
                "step_id": "s1",
                "action": {"action_type": "uia.list_windows", "target": "cmd"},
            }
        ],
    }

    res = analyzer.analyze_workflow_plan(plan)
    assert res.decision == AutomationSafetyDecision.ALLOW
