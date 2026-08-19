"""Unit tests for Phase 6.5 Workflow Engine domain models and Pydantic schemas."""

from app.automation.workflow.models import (
    ActionType,
    BackoffPolicy,
    RecoveryPolicy,
    RecoveryStrategy,
    RetryPolicy,
    VerificationCondition,
    VerificationType,
    WorkflowAction,
    WorkflowExecutionMode,
    WorkflowPlan,
    WorkflowStep,
)


def test_workflow_plan_model_instantiation():
    step1 = WorkflowStep(
        order=1,
        name="Test Step",
        action=WorkflowAction(action_type=ActionType.LAUNCH_APP, target="cmd"),
        verification=VerificationCondition(
            condition_type=VerificationType.PROCESS_RUNNING, target="cmd"
        ),
    )

    plan = WorkflowPlan(
        name="Test Workflow",
        description="A test workflow plan",
        execution_mode=WorkflowExecutionMode.SIMULATE,
        steps=[step1],
    )

    assert plan.workflow_id.startswith("wf_")
    assert len(plan.steps) == 1
    assert plan.steps[0].name == "Test Step"
    assert plan.steps[0].action.action_type == ActionType.LAUNCH_APP


def test_retry_and_recovery_policy_defaults():
    retry = RetryPolicy()
    assert retry.max_attempts == 3
    assert retry.is_idempotent is True
    assert retry.backoff == BackoffPolicy.FIXED

    recovery = RecoveryPolicy()
    assert recovery.strategy == RecoveryStrategy.RE_RESOLVE_TARGET
    assert recovery.max_recovery_attempts == 2
