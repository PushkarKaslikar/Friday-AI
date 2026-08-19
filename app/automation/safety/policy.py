"""Automation Safety Policy enforcing blast-radius, confirmation rules, rate limits, and loop protection."""

import threading
import time
from typing import Any

from app.automation.safety.models import (
    AutomationBlastRadius,
    AutomationSafetyDecision,
    AutomationSafetyEvaluation,
    AutomationSafetyMode,
    AutomationSafetyReasonCode,
)
from app.tools.base.risk import ToolRiskLevel

DESTRUCTIVE_KEYWORDS: set[str] = {
    "delete",
    "remove",
    "erase",
    "format",
    "shutdown",
    "restart",
    "terminate",
    "kill",
    "destroy",
    "uninstall",
    "overwrite",
}

POWER_KEYWORDS: set[str] = {"shutdown", "restart", "sleep", "power"}


class AutomationSafetyPolicy:
    """Deterministic policy engine evaluating automation impact, risk, confirmation, and limits."""

    def __init__(
        self,
        mode: AutomationSafetyMode = AutomationSafetyMode.NORMAL,
        require_confirmation_high: bool = True,
        require_confirmation_critical: bool = True,
        max_steps: int = 50,
        max_duration_ms: int = 300000,
        max_blast_apps: int = 5,
        max_blast_files: int = 20,
        max_actions_per_second: int = 10,
        max_workflows_per_minute: int = 15,
        max_step_retries: int = 3,
    ) -> None:
        self._lock = threading.Lock()
        self.mode = mode
        self.require_confirmation_high = require_confirmation_high
        self.require_confirmation_critical = require_confirmation_critical
        self.max_steps = max_steps
        self.max_duration_ms = max_duration_ms
        self.max_blast_apps = max_blast_apps
        self.max_blast_files = max_blast_files
        self.max_actions_per_second = max_actions_per_second
        self.max_workflows_per_minute = max_workflows_per_minute
        self.max_step_retries = max_step_retries

        self._action_timestamps: list[float] = []
        self._workflow_timestamps: list[float] = []

    def evaluate_tool_risk(
        self,
        tool_id: str,
        risk_level: ToolRiskLevel,
        arguments: dict[str, Any] | None = None,
    ) -> AutomationSafetyEvaluation:
        """Evaluate safety decision for an individual tool execution request."""
        with self._lock:
            if self.mode == AutomationSafetyMode.LOCKDOWN:
                return AutomationSafetyEvaluation(
                    decision=AutomationSafetyDecision.AUTOMATION_DISABLED,
                    risk_level=risk_level,
                    requires_confirmation=False,
                    reason_code=AutomationSafetyReasonCode.AUTOMATION_DISABLED,
                    restrictions=["System is in LOCKDOWN mode."],
                )

            # 1. Rate limiting check
            now = time.time()
            self._action_timestamps = [
                t for t in self._action_timestamps if now - t < 1.0
            ]
            if len(self._action_timestamps) >= self.max_actions_per_second:
                return AutomationSafetyEvaluation(
                    decision=AutomationSafetyDecision.DENY,
                    risk_level=risk_level,
                    requires_confirmation=False,
                    reason_code=AutomationSafetyReasonCode.RATE_LIMITED,
                    restrictions=[
                        f"Exceeded maximum action rate ({self.max_actions_per_second}/sec)."
                    ],
                )
            self._action_timestamps.append(now)

            # 2. Check for critical or prohibited actions
            t_lower = tool_id.lower()
            is_destructive = any(kw in t_lower for kw in DESTRUCTIVE_KEYWORDS)
            is_power = any(kw in t_lower for kw in POWER_KEYWORDS)

            if is_power or (
                risk_level == ToolRiskLevel.CRITICAL
                and self.require_confirmation_critical
            ):
                return AutomationSafetyEvaluation(
                    decision=AutomationSafetyDecision.REQUIRE_CONFIRMATION,
                    risk_level=ToolRiskLevel.CRITICAL,
                    requires_confirmation=True,
                    confirmation_reason=f"Action '{tool_id}' affects critical system power or destructive state.",
                    reason_code=AutomationSafetyReasonCode.CRITICAL_RISK,
                )

            if risk_level == ToolRiskLevel.HIGH and self.require_confirmation_high:
                return AutomationSafetyEvaluation(
                    decision=AutomationSafetyDecision.REQUIRE_CONFIRMATION,
                    risk_level=ToolRiskLevel.HIGH,
                    requires_confirmation=True,
                    confirmation_reason=f"Action '{tool_id}' has HIGH risk rating and requires explicit user confirmation.",
                    reason_code=AutomationSafetyReasonCode.HIGH_RISK,
                )

            if is_destructive:
                return AutomationSafetyEvaluation(
                    decision=AutomationSafetyDecision.REQUIRE_CONFIRMATION,
                    risk_level=risk_level,
                    requires_confirmation=True,
                    confirmation_reason=f"Action '{tool_id}' carries potential destructive side effects.",
                    reason_code=AutomationSafetyReasonCode.USER_CONFIRMATION_REQUIRED,
                )

            if (
                self.mode == AutomationSafetyMode.STRICT
                and risk_level == ToolRiskLevel.MEDIUM
            ):
                return AutomationSafetyEvaluation(
                    decision=AutomationSafetyDecision.REQUIRE_CONFIRMATION,
                    risk_level=risk_level,
                    requires_confirmation=True,
                    confirmation_reason="STRICT policy mode requires confirmation for MEDIUM risk tools.",
                    reason_code=AutomationSafetyReasonCode.USER_CONFIRMATION_REQUIRED,
                )

            return AutomationSafetyEvaluation(
                decision=AutomationSafetyDecision.ALLOW,
                risk_level=risk_level,
                requires_confirmation=False,
                reason_code=AutomationSafetyReasonCode.ALLOW,
            )

    def evaluate_blast_radius(
        self, blast_radius: AutomationBlastRadius
    ) -> tuple[bool, str | None]:
        """Check whether estimated blast radius exceeds safety thresholds."""
        if blast_radius.step_count > self.max_steps:
            return (
                False,
                f"Step count {blast_radius.step_count} exceeds limit {self.max_steps}",
            )
        if blast_radius.duration_estimate_ms > self.max_duration_ms:
            return (
                False,
                f"Duration {blast_radius.duration_estimate_ms}ms exceeds limit {self.max_duration_ms}ms",
            )
        if blast_radius.app_count > self.max_blast_apps:
            return (
                False,
                f"App count {blast_radius.app_count} exceeds limit {self.max_blast_apps}",
            )
        if blast_radius.file_count > self.max_blast_files:
            return (
                False,
                f"File count {blast_radius.file_count} exceeds limit {self.max_blast_files}",
            )
        return True, None
