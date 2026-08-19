"""Phase 6.7 Automation Safety, Security, Privacy & Diagnostics Package."""

from app.automation.safety.analyzer import AutomationSafetyAnalyzer
from app.automation.safety.audit import AutomationAuditLog
from app.automation.safety.confirmation_manager import AutomationConfirmationManager
from app.automation.safety.controller import AutomationSafetyManager
from app.automation.safety.diagnostics import AutomationSafetyDiagnostics
from app.automation.safety.kill_switch import AutomationKillSwitch
from app.automation.safety.metrics import AutomationSafetyMetrics
from app.automation.safety.models import (
    AutomationAuditEvent,
    AutomationBlastRadius,
    AutomationConfirmationRequest,
    AutomationConfirmationStatus,
    AutomationSafetyDecision,
    AutomationSafetyEvaluation,
    AutomationSafetyMode,
    AutomationSafetyReasonCode,
    AutomationSafetyState,
    KillSwitchStatus,
)
from app.automation.safety.policy import AutomationSafetyPolicy

__all__ = [
    "AutomationAuditEvent",
    "AutomationAuditLog",
    "AutomationBlastRadius",
    "AutomationConfirmationManager",
    "AutomationConfirmationRequest",
    "AutomationConfirmationStatus",
    "AutomationKillSwitch",
    "AutomationSafetyAnalyzer",
    "AutomationSafetyDecision",
    "AutomationSafetyDiagnostics",
    "AutomationSafetyEvaluation",
    "AutomationSafetyManager",
    "AutomationSafetyMetrics",
    "AutomationSafetyMode",
    "AutomationSafetyPolicy",
    "AutomationSafetyReasonCode",
    "AutomationSafetyState",
    "KillSwitchStatus",
]
