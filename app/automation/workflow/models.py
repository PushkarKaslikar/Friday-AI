"""Structured domain models and enums for Phase 6.5 Multi-Step Automation Workflow Engine."""

import time
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class WorkflowExecutionMode(str, Enum):
    """Workflow execution mode safety boundary."""

    DRY_RUN = "DRY_RUN"  # Plan validation only, zero execution
    SIMULATE = (
        "SIMULATE"  # Deterministic mock simulation, zero physical desktop changes
    )
    LIVE = "LIVE"  # Actual execution on Windows OS


class WorkflowState(str, Enum):
    """Deterministic state machine states for WorkflowEngine."""

    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    WAITING_FOR_VERIFICATION = "WAITING_FOR_VERIFICATION"
    RETRYING = "RETRYING"
    RECOVERING = "RECOVERING"
    CANCELLING = "CANCELLING"
    COMPLETED = "COMPLETED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    INTERRUPTED = "INTERRUPTED"
    ABORTED = "ABORTED"


class StepState(str, Enum):
    """Deterministic state machine states for individual WorkflowStep execution."""

    PENDING = "PENDING"
    PRECONDITION_CHECK = "PRECONDITION_CHECK"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    RETRYING = "RETRYING"
    RECOVERING = "RECOVERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"
    INTERRUPTED = "INTERRUPTED"


class FailurePolicy(str, Enum):
    """Workflow-level failure policy strategy."""

    FAIL_FAST = "FAIL_FAST"  # Abort workflow immediately upon step failure
    CONTINUE_OPTIONAL = "CONTINUE_OPTIONAL"  # Continue if failed step is optional
    PAUSE_ON_FAILURE = "PAUSE_ON_FAILURE"  # Transition to PAUSED state on failure


class RecoveryStrategy(str, Enum):
    """Step-level recovery policy strategy."""

    ABORT = "ABORT"
    RETRY = "RETRY"
    REATTACH = "REATTACH"
    REFRESH_UI = "REFRESH_UI"
    REFOCUS = "REFOCUS"
    RE_RESOLVE_TARGET = "RE_RESOLVE_TARGET"
    SKIP = "SKIP"
    PAUSE_FOR_USER = "PAUSE_FOR_USER"


class BackoffPolicy(str, Enum):
    """Retry delay backoff algorithm."""

    FIXED = "FIXED"
    EXPONENTIAL = "EXPONENTIAL"


class ActionType(str, Enum):
    """Structured action types supported by WorkflowActionRegistry."""

    # Application Actions
    LAUNCH_APP = "launch_app"
    ATTACH_APP = "attach_app"

    # Explorer Actions
    NAVIGATE_EXPLORER = "navigate_explorer"
    SELECT_EXPLORER_ITEM = "select_explorer_item"
    OPEN_EXPLORER_ITEM = "open_explorer_item"
    CREATE_EXPLORER_FOLDER = "create_explorer_folder"

    # Terminal Actions
    ATTACH_TERMINAL = "attach_terminal"
    SET_TERMINAL_CWD = "set_terminal_cwd"
    TYPE_TERMINAL_COMMAND = "type_terminal_command"

    # Window Control Actions
    FOCUS_WINDOW = "focus_window"
    MOVE_WINDOW = "move_window"
    RESIZE_WINDOW = "resize_window"
    SNAP_WINDOW = "snap_window"

    # Physical Input Actions
    MOUSE_CLICK = "mouse_click"
    TYPE_TEXT = "type_text"
    PRESS_HOTKEY = "press_hotkey"

    # Filesystem Actions
    FILESYSTEM_CREATE_FOLDER = "filesystem_create_folder"
    FILESYSTEM_COPY_FILE = "filesystem_copy_file"
    FILESYSTEM_MOVE_FILE = "filesystem_move_file"

    # Observation Actions
    CAPTURE_SCREEN = "capture_screen"
    GET_WORKSPACE_SUMMARY = "get_workspace_summary"


class VerificationType(str, Enum):
    """Verification condition types supported by VerificationRegistry."""

    WINDOW_EXISTS = "WINDOW_EXISTS"
    WINDOW_FOCUSED = "WINDOW_FOCUSED"
    WINDOW_TITLE_MATCHES = "WINDOW_TITLE_MATCHES"
    WINDOW_GEOMETRY_MATCH = "WINDOW_GEOMETRY_MATCH"
    PROCESS_RUNNING = "PROCESS_RUNNING"
    PROCESS_EXITED = "PROCESS_EXITED"
    UI_ELEMENT_EXISTS = "UI_ELEMENT_EXISTS"
    UI_ELEMENT_VISIBLE = "UI_ELEMENT_VISIBLE"
    UI_ELEMENT_ENABLED = "UI_ELEMENT_ENABLED"
    UI_ELEMENT_VALUE_EQUALS = "UI_ELEMENT_VALUE_EQUALS"
    UI_ELEMENT_CONTAINS_TEXT = "UI_ELEMENT_CONTAINS_TEXT"
    EXPLORER_PATH_EQUALS = "EXPLORER_PATH_EQUALS"
    FILE_EXISTS = "FILE_EXISTS"
    FOLDER_EXISTS = "FOLDER_EXISTS"
    FILE_NOT_EXISTS = "FILE_NOT_EXISTS"
    PROCESS_OUTPUT_CONTAINS = "PROCESS_OUTPUT_CONTAINS"
    CLIPBOARD_EQUALS = "CLIPBOARD_EQUALS"
    MONITOR_CONFIGURATION_AVAILABLE = "MONITOR_CONFIGURATION_AVAILABLE"


class VerificationOperator(str, Enum):
    """Boolean composition operator for verification conditions."""

    ALL = "ALL"
    ANY = "ANY"
    NOT = "NOT"


class VerificationCondition(BaseModel):
    """Structured state verification condition specification."""

    condition_type: VerificationType | None = Field(
        default=None, description="Primary verification condition type"
    )
    target: str | None = Field(
        default=None,
        description="Target window title, process name, path, or UI locator",
    )
    expected_value: Any | None = Field(
        default=None, description="Expected value or state for evaluation"
    )
    operator: VerificationOperator | None = Field(
        default=None, description="Composition operator (ALL, ANY, NOT)"
    )
    sub_conditions: list["VerificationCondition"] = Field(
        default_factory=list, description="Child conditions for composite verification"
    )
    timeout_ms: int = Field(
        default=3000, ge=0, le=30000, description="Verification polling timeout in ms"
    )
    poll_interval_ms: int = Field(
        default=250, ge=50, le=5000, description="Polling interval in ms"
    )


class RetryPolicy(BaseModel):
    """Step-level retry configuration."""

    max_attempts: int = Field(
        default=3, ge=1, le=10, description="Maximum retry attempts"
    )
    delay_ms: int = Field(
        default=500, ge=0, le=10000, description="Initial retry delay in ms"
    )
    backoff: BackoffPolicy = Field(
        default=BackoffPolicy.FIXED, description="Backoff algorithm"
    )
    retryable_statuses: list[str] = Field(
        default_factory=lambda: [
            "ACTION_FAILED",
            "VERIFICATION_FAILED",
            "TIMEOUT",
            "UI_ELEMENT_STALE",
        ],
        description="List of retryable status strings",
    )
    is_idempotent: bool = Field(
        default=True, description="Whether action is safe to retry without side effects"
    )


class RecoveryPolicy(BaseModel):
    """Step-level recovery policy specification."""

    strategy: RecoveryStrategy = Field(
        default=RecoveryStrategy.RE_RESOLVE_TARGET,
        description="Primary recovery strategy",
    )
    max_recovery_attempts: int = Field(
        default=2, ge=1, le=5, description="Maximum recovery attempts"
    )
    allowed_strategies: list[RecoveryStrategy] = Field(
        default_factory=lambda: [
            RecoveryStrategy.RE_RESOLVE_TARGET,
            RecoveryStrategy.REFOCUS,
            RecoveryStrategy.REATTACH,
            RecoveryStrategy.SKIP,
            RecoveryStrategy.PAUSE_FOR_USER,
            RecoveryStrategy.ABORT,
        ],
        description="Allowed recovery strategies",
    )


class WorkflowAction(BaseModel):
    """Declarative workflow action definition."""

    action_type: ActionType = Field(description="Action identifier")
    target: str | None = Field(default=None, description="Action target path or title")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Structured parameters payload"
    )
    idempotent: bool = Field(
        default=True, description="Whether action is safe for automatic retry"
    )
    supports_cancellation: bool = Field(
        default=True, description="Whether action supports cancellation"
    )
    supports_dry_run: bool = Field(
        default=True, description="Whether action supports dry-run validation"
    )
    supports_simulation: bool = Field(
        default=True, description="Whether action supports mock simulation"
    )
    risk_level: str = Field(
        default="LOW", description="Observability risk category (LOW, MEDIUM, HIGH)"
    )


class WorkflowStep(BaseModel):
    """Observable step unit within a WorkflowPlan."""

    step_id: str = Field(default_factory=lambda: f"step_{uuid4().hex[:8]}")
    name: str = Field(description="Step human-readable name")
    order: int = Field(ge=1, description="1-indexed step execution order")
    action: WorkflowAction = Field(description="Structured action definition")
    precondition: VerificationCondition | None = Field(
        default=None, description="Optional pre-execution state condition"
    )
    verification: VerificationCondition | None = Field(
        default=None, description="Post-action state verification condition"
    )
    timeout_ms: int = Field(
        default=10000, ge=100, le=120000, description="Step execution timeout in ms"
    )
    retry_policy: RetryPolicy = Field(
        default_factory=RetryPolicy, description="Retry policy"
    )
    recovery_policy: RecoveryPolicy = Field(
        default_factory=RecoveryPolicy, description="Recovery policy"
    )
    optional: bool = Field(
        default=False, description="If True, step failure does not abort workflow"
    )
    continue_on_failure: bool = Field(
        default=False,
        description="If True, continue workflow execution even if step fails",
    )
    output_variable: str | None = Field(
        default=None, description="Variable name to store step output result"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata key-value map"
    )


class WorkflowPlan(BaseModel):
    """Complete declarative multi-step automation workflow plan specification."""

    workflow_id: str = Field(default_factory=lambda: f"wf_{uuid4().hex[:8]}")
    name: str = Field(description="Workflow human-readable name")
    description: str = Field(default="", description="Workflow description")
    steps: list[WorkflowStep] = Field(description="Sequential list of workflow steps")
    timeout_ms: int = Field(
        default=60000, ge=1000, le=600000, description="Total workflow timeout in ms"
    )
    max_steps: int = Field(
        default=50, ge=1, le=100, description="Maximum allowed steps bound"
    )
    execution_mode: WorkflowExecutionMode = Field(
        default=WorkflowExecutionMode.SIMULATE, description="Execution safety mode"
    )
    failure_policy: FailurePolicy = Field(
        default=FailurePolicy.FAIL_FAST, description="Failure handling policy"
    )
    variables: dict[str, Any] = Field(
        default_factory=dict, description="Initial workflow variable bindings"
    )
    source: str = Field(default="user", description="Workflow source identifier")
    created_at: float = Field(
        default_factory=time.time, description="Unix creation timestamp"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata dictionary"
    )


class ActionResult(BaseModel):
    """Structured result returned by WorkflowActionRegistry after action execution."""

    status: str = Field(
        description="SUCCESS, FAILED, CANCELLED, TIMEOUT, INTERRUPTED, INVALID"
    )
    action_id: str = Field(description="Action identifier string")
    duration_ms: float = Field(default=0.0, description="Action duration in ms")
    output: Any | None = Field(default=None, description="Action output data payload")
    error: str | None = Field(default=None, description="Error message if failed")
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    """Structured result returned by StepVerifier after evaluating a condition."""

    status: str = Field(description="PASSED, FAILED, TIMEOUT, SKIPPED")
    condition_type: str | None = Field(
        default=None, description="Evaluated condition type"
    )
    expected: Any | None = Field(default=None, description="Expected value")
    actual: Any | None = Field(default=None, description="Actual observed value")
    elapsed_ms: float = Field(default=0.0, description="Elapsed time in ms")
    attempts: int = Field(default=1, description="Polling attempt count")
    reason: str | None = Field(
        default=None, description="Failure or success explanation"
    )


class StepResult(BaseModel):
    """Structured execution result for an individual WorkflowStep."""

    step_id: str = Field(description="Step ID")
    status: StepState = Field(description="Final step state")
    action_result: ActionResult | None = Field(
        default=None, description="Action result"
    )
    verification_result: VerificationResult | None = Field(
        default=None, description="Postcondition verification result"
    )
    attempts: int = Field(default=1, description="Total action execution attempts")
    duration_ms: float = Field(default=0.0, description="Total step duration in ms")
    failure_reason: str | None = Field(default=None, description="Failure explanation")
    recovery_attempts: int = Field(default=0, description="Recovery attempt count")


class WorkflowResult(BaseModel):
    """Structured outcome result returned after complete WorkflowPlan execution."""

    workflow_id: str = Field(description="Workflow ID")
    status: WorkflowState = Field(description="Final workflow state")
    completed_steps: int = Field(
        default=0, description="Count of successfully completed steps"
    )
    failed_step: str | None = Field(default=None, description="Step ID of failed step")
    duration_ms: float = Field(
        default=0.0, description="Total execution duration in ms"
    )
    outputs: dict[str, Any] = Field(
        default_factory=dict, description="Exported workflow variables and step outputs"
    )
    errors: list[str] = Field(
        default_factory=list, description="List of error messages"
    )
    verification_summary: dict[str, int] = Field(
        default_factory=dict, description="Summary counts of verified vs failed checks"
    )
    retry_count: int = Field(
        default=0, description="Total retries performed across workflow"
    )
    recovery_count: int = Field(
        default=0, description="Total recovery attempts performed"
    )
    step_results: list[StepResult] = Field(
        default_factory=list, description="Ordered step execution results"
    )


class WorkflowReport(BaseModel):
    """Human-readable diagnostic report summarizing workflow execution."""

    workflow_id: str
    name: str
    status: WorkflowState
    execution_mode: WorkflowExecutionMode
    duration_ms: float
    total_steps: int
    completed_steps: int
    failed_step: str | None = None
    summary: str
    sanitized_variables: dict[str, Any] = Field(default_factory=dict)
