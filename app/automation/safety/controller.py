"""Subsystem coordinator managing global automation safety states, resource locks, and preflight governance."""

import threading
from typing import TYPE_CHECKING, Any, Optional

from app.automation.safety.analyzer import AutomationSafetyAnalyzer
from app.automation.safety.audit import AutomationAuditLog
from app.automation.safety.confirmation_manager import AutomationConfirmationManager
from app.automation.safety.kill_switch import AutomationKillSwitch
from app.automation.safety.metrics import AutomationSafetyMetrics
from app.automation.safety.models import (
    AutomationConfirmationRequest,
    AutomationConfirmationStatus,
    AutomationSafetyDecision,
    AutomationSafetyEvaluation,
    AutomationSafetyMode,
    AutomationSafetyReasonCode,
    AutomationSafetyState,
)
from app.automation.safety.policy import AutomationSafetyPolicy
from app.logging import logger
from app.services.events.event_bus import EventBus
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel

if TYPE_CHECKING:
    from app.automation.workflow.workflow_controller import WorkflowManager


class AutomationSafetyManager:
    """Central cross-cutting safety coordinator for Friday AI Assistant computer automation."""

    def __init__(
        self,
        policy: AutomationSafetyPolicy | None = None,
        analyzer: AutomationSafetyAnalyzer | None = None,
        kill_switch: AutomationKillSwitch | None = None,
        confirmation_manager: AutomationConfirmationManager | None = None,
        audit_log: AutomationAuditLog | None = None,
        metrics: AutomationSafetyMetrics | None = None,
        event_bus: EventBus | None = None,
        workflow_manager: Optional["WorkflowManager"] = None,
    ) -> None:
        self._lock = threading.Lock()
        self.policy = policy or AutomationSafetyPolicy()
        self.analyzer = analyzer or AutomationSafetyAnalyzer(policy=self.policy)
        self.kill_switch = kill_switch or AutomationKillSwitch()
        self.confirmation_manager = (
            confirmation_manager or AutomationConfirmationManager()
        )
        self.audit_log = audit_log or AutomationAuditLog()
        self.metrics = metrics or AutomationSafetyMetrics()
        self.event_bus = event_bus or EventBus()
        self.workflow_manager = workflow_manager

        self._state = AutomationSafetyState.READY
        self._active_resource_locks: set[str] = set()

    @property
    def state(self) -> AutomationSafetyState:
        with self._lock:
            return self._state

    def set_lockdown(self, enabled: bool) -> None:
        """Enable or disable global lockdown mode."""
        with self._lock:
            if enabled:
                self.policy.mode = AutomationSafetyMode.LOCKDOWN
                self._state = AutomationSafetyState.LOCKDOWN
                self.metrics.increment_lockdown_events()
                logger.warning(
                    "AutomationSafetyManager: System transitioned into LOCKDOWN mode."
                )
            else:
                self.policy.mode = AutomationSafetyMode.NORMAL
                self._state = AutomationSafetyState.READY
                logger.info(
                    "AutomationSafetyManager: LOCKDOWN mode disabled. System returned to READY state."
                )

    def preflight_tool_check(
        self,
        tool_id: str,
        arguments: dict[str, Any] | None = None,
        granted_permissions: set[ToolPermission] | None = None,
    ) -> AutomationSafetyEvaluation:
        """Perform preflight safety check for an individual tool request."""
        self.metrics.increment_evaluations()

        if self.kill_switch.is_triggered:
            self.metrics.increment_kill_switch_triggers()
            eval_res = AutomationSafetyEvaluation(
                decision=AutomationSafetyDecision.KILLSWITCHED,
                risk_level=ToolRiskLevel.HIGH,
                requires_confirmation=False,
                reason_code=AutomationSafetyReasonCode.KILL_SWITCH,
                restrictions=["Global emergency kill switch is TRIGGERED."],
            )
            self.audit_log.record_event(
                tool_id,
                ToolRiskLevel.HIGH,
                eval_res.decision,
                eval_res.reason_code,
                "DENIED",
            )
            return eval_res

        if self.policy.mode == AutomationSafetyMode.LOCKDOWN:
            eval_res = AutomationSafetyEvaluation(
                decision=AutomationSafetyDecision.AUTOMATION_DISABLED,
                risk_level=ToolRiskLevel.HIGH,
                requires_confirmation=False,
                reason_code=AutomationSafetyReasonCode.AUTOMATION_DISABLED,
                restrictions=["System is in LOCKDOWN mode."],
            )
            self.audit_log.record_event(
                tool_id,
                ToolRiskLevel.HIGH,
                eval_res.decision,
                eval_res.reason_code,
                "DENIED",
            )
            return eval_res

        eval_res = self.analyzer.analyze_tool_request(
            tool_id, arguments, granted_permissions
        )
        if eval_res.decision == AutomationSafetyDecision.ALLOW:
            self.metrics.increment_allowed()
        elif eval_res.decision == AutomationSafetyDecision.REQUIRE_CONFIRMATION:
            self.metrics.increment_confirmation_requested()
        else:
            self.metrics.increment_denied()

        self.audit_log.record_event(
            tool_id,
            eval_res.risk_level,
            eval_res.decision,
            eval_res.reason_code,
            "PREFLIGHT_DONE",
        )
        return eval_res

    def preflight_workflow_check(
        self,
        plan_dict_or_obj: Any,
        granted_permissions: set[ToolPermission] | None = None,
    ) -> AutomationSafetyEvaluation:
        """Perform preflight safety check for a multi-step WorkflowPlan."""
        self.metrics.increment_evaluations()

        if self.kill_switch.is_triggered:
            self.metrics.increment_kill_switch_triggers()
            return AutomationSafetyEvaluation(
                decision=AutomationSafetyDecision.KILLSWITCHED,
                risk_level=ToolRiskLevel.HIGH,
                requires_confirmation=False,
                reason_code=AutomationSafetyReasonCode.KILL_SWITCH,
                restrictions=["Global emergency kill switch is TRIGGERED."],
            )

        if self.policy.mode == AutomationSafetyMode.LOCKDOWN:
            return AutomationSafetyEvaluation(
                decision=AutomationSafetyDecision.AUTOMATION_DISABLED,
                risk_level=ToolRiskLevel.HIGH,
                requires_confirmation=False,
                reason_code=AutomationSafetyReasonCode.AUTOMATION_DISABLED,
                restrictions=["System is in LOCKDOWN mode."],
            )

        eval_res = self.analyzer.analyze_workflow_plan(
            plan_dict_or_obj, granted_permissions
        )
        if eval_res.decision == AutomationSafetyDecision.ALLOW:
            self.metrics.increment_allowed()
        elif eval_res.decision == AutomationSafetyDecision.REQUIRE_CONFIRMATION:
            self.metrics.increment_confirmation_requested()
        else:
            self.metrics.increment_denied()

        wf_id = (
            getattr(plan_dict_or_obj, "workflow_id", None)
            if hasattr(plan_dict_or_obj, "workflow_id")
            else (
                plan_dict_or_obj.get("workflow_id")
                if isinstance(plan_dict_or_obj, dict)
                else None
            )
        )
        self.audit_log.record_event(
            tool_name="workflow.execute_sequence",
            risk_level=eval_res.risk_level,
            decision=eval_res.decision,
            reason_code=eval_res.reason_code,
            execution_status="PREFLIGHT_DONE",
            workflow_id=wf_id,
        )
        return eval_res

    def request_confirmation(
        self,
        reason: str,
        risk_level: ToolRiskLevel,
        action_summary: str,
        affected_resources: list[str] | None = None,
        workflow_id: str | None = None,
    ) -> AutomationConfirmationRequest:
        """Create structured user confirmation request."""
        with self._lock:
            self._state = AutomationSafetyState.WAITING_CONFIRMATION
        return self.confirmation_manager.create_request(
            reason=reason,
            risk_level=risk_level,
            action_summary=action_summary,
            affected_resources=affected_resources,
            workflow_id=workflow_id,
        )

    def resolve_confirmation(self, confirmation_id: str, confirmed: bool) -> bool:
        """Resolve pending confirmation request via explicit trusted interaction."""
        status = self.confirmation_manager.resolve_confirmation(
            confirmation_id, confirmed, trusted_source=True
        )
        with self._lock:
            if status == AutomationConfirmationStatus.CONFIRMED:
                self.metrics.increment_confirmation_accepted()
                self._state = AutomationSafetyState.RUNNING
                return True
            else:
                self.metrics.increment_confirmation_denied()
                self._state = AutomationSafetyState.READY
                return False

    def trigger_kill_switch(
        self, reason: str = "Explicit emergency kill switch triggered"
    ) -> None:
        """Trigger emergency stop across all computer automation."""
        with self._lock:
            self.kill_switch.trigger(reason)
            self._state = AutomationSafetyState.KILL_SWITCHED
            self.metrics.increment_kill_switch_triggers()
            self.confirmation_manager.cancel_all("Kill switch triggered")
            self._active_resource_locks.clear()

        if self.workflow_manager:
            self.workflow_manager.cancel_active_workflow(reason)

    def handle_user_interruption(
        self, reason: str = "Physical user interference"
    ) -> None:
        """Handle physical mouse or keyboard user interference."""
        with self._lock:
            self._state = AutomationSafetyState.INTERRUPTED
            self.metrics.increment_user_interruptions()
            self.confirmation_manager.cancel_all("User interruption")
            self._active_resource_locks.clear()

        if self.workflow_manager:
            self.workflow_manager.handle_user_interruption(reason)

    def handle_failsafe_aborted(
        self, reason: str = "Top-left mouse failsafe triggered"
    ) -> None:
        """Handle physical top-left mouse failsafe corner trigger."""
        with self._lock:
            self._state = AutomationSafetyState.FAILSAFE_ABORTED
            self.metrics.increment_failsafe_triggers()
            self.confirmation_manager.cancel_all("Failsafe triggered")
            self._active_resource_locks.clear()

        if self.workflow_manager:
            self.workflow_manager.handle_failsafe_trigger(reason)

    def acquire_resource_lock(self, resource_name: str) -> bool:
        """Acquire lock on a named automation resource."""
        with self._lock:
            if resource_name in self._active_resource_locks:
                return False
            self._active_resource_locks.add(resource_name)
            return True

    def release_resource_lock(self, resource_name: str) -> None:
        """Release lock on a named automation resource."""
        with self._lock:
            self._active_resource_locks.discard(resource_name)

    def postflight_cleanup(self) -> None:
        """Postflight cleanup releasing locks and resetting state to READY."""
        with self._lock:
            self._active_resource_locks.clear()
            if self._state not in (
                AutomationSafetyState.KILL_SWITCHED,
                AutomationSafetyState.LOCKDOWN,
            ):
                self._state = AutomationSafetyState.READY
