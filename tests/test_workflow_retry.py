"""Unit tests for WorkflowEngine step retry policy and idempotency rules."""

from unittest.mock import MagicMock

from app.automation.workflow.action_registry import WorkflowActionRegistry
from app.automation.workflow.engine import WorkflowEngine
from app.automation.workflow.models import (
    ActionResult,
    ActionType,
    RetryPolicy,
    WorkflowAction,
    WorkflowExecutionMode,
    WorkflowPlan,
    WorkflowState,
    WorkflowStep,
)


def test_retry_policy_retries_on_action_failure():
    action_reg = MagicMock(spec=WorkflowActionRegistry)
    action_reg.has_handler.return_value = True

    # Action fails twice then succeeds
    action_reg.execute_action.side_effect = [
        ActionResult(status="FAILED", action_id="launch_app", error="Temp error 1"),
        ActionResult(status="FAILED", action_id="launch_app", error="Temp error 2"),
        ActionResult(
            status="SUCCESS", action_id="launch_app", output={"launched": True}
        ),
    ]

    engine = WorkflowEngine(action_registry=action_reg)

    plan = WorkflowPlan(
        name="Retry Workflow",
        execution_mode=WorkflowExecutionMode.LIVE,
        steps=[
            WorkflowStep(
                order=1,
                name="Failing Step",
                action=WorkflowAction(action_type=ActionType.LAUNCH_APP, target="cmd"),
                retry_policy=RetryPolicy(
                    max_attempts=3, delay_ms=10, is_idempotent=True
                ),
            )
        ],
    )

    res = engine.execute_workflow(plan)

    assert res.status == WorkflowState.COMPLETED
    assert res.step_results[0].attempts == 3
    assert res.retry_count == 2


def test_non_idempotent_action_skips_retry():
    action_reg = MagicMock(spec=WorkflowActionRegistry)
    action_reg.has_handler.return_value = True
    action_reg.execute_action.return_value = ActionResult(
        status="FAILED", action_id="mouse_click", error="Click failed"
    )

    engine = WorkflowEngine(action_registry=action_reg)

    plan = WorkflowPlan(
        name="Non-Idempotent Workflow",
        execution_mode=WorkflowExecutionMode.LIVE,
        steps=[
            WorkflowStep(
                order=1,
                name="Non-Idempotent Click",
                action=WorkflowAction(
                    action_type=ActionType.MOUSE_CLICK, idempotent=False
                ),
                retry_policy=RetryPolicy(
                    max_attempts=3, delay_ms=10, is_idempotent=False
                ),
            )
        ],
    )

    res = engine.execute_workflow(plan)

    assert res.status == WorkflowState.FAILED
    assert res.step_results[0].attempts == 1
