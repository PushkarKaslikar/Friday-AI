"""Custom exception hierarchy for Phase 6.5 Workflow Engine Subsystem."""

from typing import Any

from app.exceptions.base import FridayBaseException


class WorkflowError(FridayBaseException):
    """Base exception class for all Phase 6.5 Workflow Engine errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        workflow_id: str | None = None,
        step_id: str | None = None,
    ) -> None:
        merged_details = details or {}
        if workflow_id:
            merged_details["workflow_id"] = workflow_id
        if step_id:
            merged_details["step_id"] = step_id
        super().__init__(message=message, details=merged_details)


class WorkflowInvalidError(WorkflowError):
    """Raised when a WorkflowPlan fails pre-flight validation."""


class StepInvalidError(WorkflowError):
    """Raised when a WorkflowStep definition is malformed or invalid."""


class PreconditionFailedError(WorkflowError):
    """Raised when a step's precondition verification fails prior to action execution."""


class ActionFailedError(WorkflowError):
    """Raised when an action execution fails or returns an error status."""


class VerificationFailedError(WorkflowError):
    """Raised when a step's post-action state verification condition fails."""


class VerificationTimeoutError(WorkflowError):
    """Raised when a verification condition fails to become true within the timeout window."""


class RetryExhaustedError(WorkflowError):
    """Raised when step retry attempts reach the maximum configured limit."""


class RecoveryFailedError(WorkflowError):
    """Raised when step recovery policy strategies fail to recover execution state."""


class ResourceBusyError(WorkflowError):
    """Raised when attempting to execute a live workflow while another live workflow or input lock is active."""


class WorkflowTimeoutError(WorkflowError):
    """Raised when total workflow execution time exceeds max_workflow_timeout_ms."""


class WorkflowCancelledError(WorkflowError):
    """Raised when a workflow execution is cancelled via CancellationToken."""


class WorkflowInterruptedError(WorkflowError):
    """Raised when physical user input is detected by Phase 6.2 InterruptionMonitor."""


class FailsafeAbortedError(WorkflowError):
    """Raised when Phase 6.2 top-left mouse failsafe is triggered."""


class ApplicationUnavailableError(WorkflowError):
    """Raised when a required application or adapter is missing or unavailable."""


class UIElementStaleError(WorkflowError):
    """Raised when a UIA element reference becomes stale during workflow execution."""


class VariableInvalidError(WorkflowError):
    """Raised when a workflow variable reference is missing, malformed, or invalid."""


class UnsupportedActionError(WorkflowError):
    """Raised when an action type is not supported by WorkflowActionRegistry."""


class UnsupportedVerificationError(WorkflowError):
    """Raised when a verification type is not supported by VerificationRegistry."""
