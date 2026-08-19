"""Typed event payload models for Phase 6.5 Workflow Engine EventBus notifications."""

import time

from pydantic import BaseModel, Field

from app.automation.workflow.models import (
    StepState,
    WorkflowExecutionMode,
    WorkflowState,
)


class WorkflowBaseEvent(BaseModel):
    """Base event model for all workflow EventBus events."""

    workflow_id: str
    timestamp: float = Field(default_factory=time.time)


class WorkflowStartedEvent(WorkflowBaseEvent):
    event_type: str = "WorkflowStarted"
    name: str
    execution_mode: WorkflowExecutionMode
    total_steps: int


class WorkflowValidatedEvent(WorkflowBaseEvent):
    event_type: str = "WorkflowValidated"
    name: str
    total_steps: int
    execution_mode: WorkflowExecutionMode


class WorkflowStepStartedEvent(WorkflowBaseEvent):
    event_type: str = "WorkflowStepStarted"
    step_id: str
    step_name: str
    order: int
    action_type: str


class WorkflowStepCompletedEvent(WorkflowBaseEvent):
    event_type: str = "WorkflowStepCompleted"
    step_id: str
    step_name: str
    order: int
    status: StepState
    duration_ms: float


class WorkflowStepVerificationStartedEvent(WorkflowBaseEvent):
    event_type: str = "WorkflowStepVerificationStarted"
    step_id: str
    condition_type: str


class WorkflowStepVerifiedEvent(WorkflowBaseEvent):
    event_type: str = "WorkflowStepVerified"
    step_id: str
    condition_type: str
    passed: bool
    elapsed_ms: float


class WorkflowStepRetryingEvent(WorkflowBaseEvent):
    event_type: str = "WorkflowStepRetrying"
    step_id: str
    attempt: int
    max_attempts: int
    reason: str


class WorkflowStepRecoveringEvent(WorkflowBaseEvent):
    event_type: str = "WorkflowStepRecovering"
    step_id: str
    strategy: str
    attempt: int


class WorkflowPausedEvent(WorkflowBaseEvent):
    event_type: str = "WorkflowPaused"
    reason: str
    step_id: str | None = None


class WorkflowResumedEvent(WorkflowBaseEvent):
    event_type: str = "WorkflowResumed"
    resumed_from_step: str


class WorkflowCancelledEvent(WorkflowBaseEvent):
    event_type: str = "WorkflowCancelled"
    reason: str


class WorkflowInterruptedEvent(WorkflowBaseEvent):
    event_type: str = "WorkflowInterrupted"
    reason: str


class WorkflowCompletedEvent(WorkflowBaseEvent):
    event_type: str = "WorkflowCompleted"
    status: WorkflowState
    completed_steps: int
    duration_ms: float


class WorkflowFailedEvent(WorkflowBaseEvent):
    event_type: str = "WorkflowFailed"
    failed_step_id: str | None = None
    reason: str
    duration_ms: float


class WorkflowAbortedEvent(WorkflowBaseEvent):
    event_type: str = "WorkflowAborted"
    reason: str
