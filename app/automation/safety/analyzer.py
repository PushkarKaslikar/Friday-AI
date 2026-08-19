"""Automation Safety Analyzer performing deterministic preflight inspection of tool calls and WorkflowPlans."""

from typing import Any

from app.automation.safety.models import (
    AutomationBlastRadius,
    AutomationSafetyDecision,
    AutomationSafetyEvaluation,
    AutomationSafetyReasonCode,
)
from app.automation.safety.policy import AutomationSafetyPolicy
from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.registry.tool_registry import ToolRegistry


class AutomationSafetyAnalyzer:
    """Deterministic analyzer inspecting workflow step sequences and individual tool requests."""

    def __init__(
        self,
        policy: AutomationSafetyPolicy | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self.policy = policy or AutomationSafetyPolicy()
        self.tool_registry = tool_registry or ToolRegistry()

    def analyze_tool_request(
        self,
        tool_id: str,
        arguments: dict[str, Any] | None = None,
        granted_permissions: set[ToolPermission] | None = None,
    ) -> AutomationSafetyEvaluation:
        """Analyze preflight safety of a single tool execution request."""
        tool = self.tool_registry.get_tool(tool_id)
        if not tool:
            return AutomationSafetyEvaluation(
                decision=AutomationSafetyDecision.DENY,
                risk_level=ToolRiskLevel.HIGH,
                requires_confirmation=False,
                reason_code=AutomationSafetyReasonCode.UNSUPPORTED_ACTION,
                restrictions=[f"Tool '{tool_id}' is not registered in ToolRegistry."],
            )

        meta: ToolMetadata = tool.metadata

        # Check required permissions if granted set provided
        if granted_permissions is not None:
            missing = [p for p in meta.permissions if p not in granted_permissions]
            if missing:
                return AutomationSafetyEvaluation(
                    decision=AutomationSafetyDecision.DENY,
                    risk_level=meta.risk_level,
                    requires_confirmation=False,
                    reason_code=AutomationSafetyReasonCode.PRIVACY_RESTRICTED,
                    restrictions=[f"Missing permissions: {[p.value for p in missing]}"],
                )

        return self.policy.evaluate_tool_risk(tool_id, meta.risk_level, arguments)

    def analyze_workflow_plan(
        self,
        plan_dict_or_obj: Any,
        granted_permissions: set[ToolPermission] | None = None,
    ) -> AutomationSafetyEvaluation:
        """Inspect a multi-step WorkflowPlan and aggregate effective risk and blast radius."""
        steps: list[Any] = []
        if hasattr(plan_dict_or_obj, "steps"):
            steps = getattr(plan_dict_or_obj, "steps", [])
        elif isinstance(plan_dict_or_obj, dict):
            steps = plan_dict_or_obj.get("steps", [])

        if not steps:
            return AutomationSafetyEvaluation(
                decision=AutomationSafetyDecision.ALLOW,
                risk_level=ToolRiskLevel.LOW,
                requires_confirmation=False,
                reason_code=AutomationSafetyReasonCode.ALLOW,
            )

        # 1. Aggregate effective risk level across all steps (max risk wins, never average)
        max_risk = ToolRiskLevel.LOW
        requires_conf = False
        reasons: list[str] = []
        target_apps: set[str] = set()

        risk_order = {
            ToolRiskLevel.LOW: 1,
            ToolRiskLevel.MEDIUM: 2,
            ToolRiskLevel.HIGH: 3,
            ToolRiskLevel.CRITICAL: 4,
        }

        for step in steps:
            action = getattr(step, "action", None) or (
                step.get("action") if isinstance(step, dict) else None
            )
            target = (
                getattr(action, "target", None)
                if action
                else (action.get("target") if isinstance(action, dict) else None)
            )
            tool_id = (
                getattr(action, "action_type", None)
                if action
                else (action.get("action_type") if isinstance(action, dict) else None)
            )
            if tool_id and hasattr(tool_id, "value"):
                tool_id = tool_id.value

            if target:
                target_apps.add(str(target))

            step_risk = ToolRiskLevel.LOW
            if tool_id:
                tool_eval = self.analyze_tool_request(
                    str(tool_id), granted_permissions=granted_permissions
                )
                if tool_eval.decision == AutomationSafetyDecision.DENY:
                    return tool_eval
                step_risk = tool_eval.risk_level
                if tool_eval.requires_confirmation:
                    requires_conf = True
                    if tool_eval.confirmation_reason:
                        reasons.append(tool_eval.confirmation_reason)

            if risk_order[step_risk] > risk_order[max_risk]:
                max_risk = step_risk

        # 2. Estimate Blast Radius
        blast = AutomationBlastRadius(
            step_count=len(steps),
            app_count=max(1, len(target_apps)),
            duration_estimate_ms=len(steps) * 1000,
        )

        ok, blast_err = self.policy.evaluate_blast_radius(blast)
        if not ok:
            return AutomationSafetyEvaluation(
                decision=AutomationSafetyDecision.DENY,
                risk_level=max_risk,
                requires_confirmation=False,
                blast_radius=blast,
                reason_code=AutomationSafetyReasonCode.BLAST_RADIUS_EXCEEDED,
                restrictions=[blast_err or "Blast radius limit exceeded."],
            )

        if max_risk in (ToolRiskLevel.HIGH, ToolRiskLevel.CRITICAL) or requires_conf:
            return AutomationSafetyEvaluation(
                decision=AutomationSafetyDecision.REQUIRE_CONFIRMATION,
                risk_level=max_risk,
                requires_confirmation=True,
                confirmation_reason=(
                    "; ".join(reasons)
                    if reasons
                    else f"Workflow contains {max_risk.value} risk operations."
                ),
                blast_radius=blast,
                reason_code=(
                    AutomationSafetyReasonCode.HIGH_RISK
                    if max_risk == ToolRiskLevel.HIGH
                    else AutomationSafetyReasonCode.CRITICAL_RISK
                ),
            )

        return AutomationSafetyEvaluation(
            decision=AutomationSafetyDecision.ALLOW,
            risk_level=max_risk,
            requires_confirmation=False,
            blast_radius=blast,
            reason_code=AutomationSafetyReasonCode.ALLOW,
        )
