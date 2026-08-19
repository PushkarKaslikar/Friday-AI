"""Domain models, enums, and Pydantic schemas for Phase 6.7 Safety Governance."""

import uuid
from enum import Enum

from pydantic import BaseModel, Field

from app.tools.base.risk import ToolRiskLevel
from app.utilities.system_utils import get_timestamp_str


class AutomationSafetyState(str, Enum):
    """Global state machine status for computer automation governance."""

    IDLE = "IDLE"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    PAUSED_USER = "PAUSED_USER"
    PAUSED_SAFETY = "PAUSED_SAFETY"
    INTERRUPTED = "INTERRUPTED"
    KILL_SWITCHED = "KILL_SWITCHED"
    FAILSAFE_ABORTED = "FAILSAFE_ABORTED"
    CANCELLING = "CANCELLING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    LOCKDOWN = "LOCKDOWN"
    SHUTTING_DOWN = "SHUTTING_DOWN"


class AutomationSafetyMode(str, Enum):
    """Execution safety policy modes."""

    NORMAL = "NORMAL"
    STRICT = "STRICT"
    LOCKDOWN = "LOCKDOWN"


class AutomationSafetyReasonCode(str, Enum):
    """Detailed rationale classification for safety preflight decisions."""

    ALLOW = "ALLOW"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL_RISK = "CRITICAL_RISK"
    USER_CONFIRMATION_REQUIRED = "USER_CONFIRMATION_REQUIRED"
    BLAST_RADIUS_EXCEEDED = "BLAST_RADIUS_EXCEEDED"
    RATE_LIMITED = "RATE_LIMITED"
    LOOP_DETECTED = "LOOP_DETECTED"
    INPUT_CONFLICT = "INPUT_CONFLICT"
    USER_INTERRUPTED = "USER_INTERRUPTED"
    FAILSAFE = "FAILSAFE"
    KILL_SWITCH = "KILL_SWITCH"
    UNSUPPORTED_ACTION = "UNSUPPORTED_ACTION"
    UNAVAILABLE_RESOURCE = "UNAVAILABLE_RESOURCE"
    PRIVACY_RESTRICTED = "PRIVACY_RESTRICTED"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    POLICY_DISABLED = "POLICY_DISABLED"
    AUTOMATION_DISABLED = "AUTOMATION_DISABLED"


class AutomationSafetyDecision(str, Enum):
    """Core outcome decision returned by AutomationSafetyAnalyzer."""

    ALLOW = "ALLOW"
    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"
    DENY = "DENY"
    KILLSWITCHED = "KILLSWITCHED"
    PAUSED = "PAUSED"
    UNAVAILABLE = "UNAVAILABLE"
    AUTOMATION_DISABLED = "AUTOMATION_DISABLED"


class AutomationConfirmationStatus(str, Enum):
    """Lifecycle status of a structured confirmation request."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class KillSwitchStatus(str, Enum):
    """Global emergency stop status."""

    ARMED = "ARMED"
    TRIGGERED = "TRIGGERED"
    RESETTING = "RESETTING"


class AutomationBlastRadius(BaseModel):
    """Quantified operational impact metric bounds for automation requests."""

    step_count: int = Field(default=1, ge=0, description="Total steps in sequence")
    app_count: int = Field(
        default=1, ge=0, description="Targeted unique applications count"
    )
    window_count: int = Field(
        default=1, ge=0, description="Targeted unique windows count"
    )
    file_count: int = Field(
        default=0, ge=0, description="Targeted files or filesystem mutations count"
    )
    input_count: int = Field(
        default=1, ge=0, description="Targeted physical input actions count"
    )
    duration_estimate_ms: int = Field(
        default=1000, ge=0, description="Estimated execution duration in milliseconds"
    )


class AutomationSafetyEvaluation(BaseModel):
    """Complete safety decision result object."""

    decision: AutomationSafetyDecision = Field(
        description="Core safety decision outcome"
    )
    risk_level: ToolRiskLevel = Field(
        default=ToolRiskLevel.LOW, description="Aggregated risk classification"
    )
    requires_confirmation: bool = Field(
        default=False, description="Whether explicit user confirmation is needed"
    )
    confirmation_reason: str | None = Field(
        default=None, description="Human-readable rationale for confirmation"
    )
    blast_radius: AutomationBlastRadius = Field(
        default_factory=AutomationBlastRadius, description="Quantified impact bounds"
    )
    restrictions: list[str] = Field(
        default_factory=list, description="List of active restrictions or policy limits"
    )
    reason_code: AutomationSafetyReasonCode = Field(
        default=AutomationSafetyReasonCode.ALLOW,
        description="Reason code classification",
    )


class AutomationConfirmationRequest(BaseModel):
    """Structured user confirmation request model."""

    confirmation_id: str = Field(
        default_factory=lambda: f"conf_{uuid.uuid4().hex[:8]}",
        description="Unique confirmation ID",
    )
    workflow_id: str | None = Field(default=None, description="Associated workflow ID")
    tool_id: str | None = Field(default=None, description="Associated tool ID")
    reason: str = Field(
        description="Human-readable explanation of why confirmation is required"
    )
    risk_level: ToolRiskLevel = Field(description="Risk classification")
    action_summary: str = Field(
        description="User-friendly summary of proposed side effects"
    )
    affected_resources: list[str] = Field(
        default_factory=list, description="Target applications or resources"
    )
    expiration_ms: int = Field(
        default=30000,
        ge=5000,
        le=300000,
        description="Expiration duration in milliseconds",
    )
    requested_at: str = Field(
        default_factory=get_timestamp_str, description="ISO timestamp"
    )
    fingerprint: str = Field(description="Action fingerprint for replay protection")
    status: AutomationConfirmationStatus = Field(
        default=AutomationConfirmationStatus.PENDING,
        description="Current confirmation status",
    )


class AutomationAuditEvent(BaseModel):
    """Structured privacy-preserving audit log record."""

    event_id: str = Field(
        default_factory=lambda: f"audit_{uuid.uuid4().hex[:8]}",
        description="Unique audit event ID",
    )
    timestamp: str = Field(
        default_factory=get_timestamp_str, description="ISO timestamp"
    )
    session_id: str = Field(
        default="session_main", description="Active user session ID"
    )
    workflow_id: str | None = Field(default=None, description="Workflow plan ID")
    tool_name: str = Field(description="Tool or operation identifier")
    action_type: str = Field(default="EXECUTE", description="Action type description")
    risk_level: ToolRiskLevel = Field(description="Risk classification")
    decision: AutomationSafetyDecision = Field(description="Preflight safety decision")
    confirmation_status: AutomationConfirmationStatus | None = Field(
        default=None, description="Confirmation status if applicable"
    )
    execution_status: str = Field(description="Execution result status")
    reason_code: AutomationSafetyReasonCode = Field(description="Safety reason code")
    duration_ms: float = Field(default=0.0, description="Execution duration in ms")
