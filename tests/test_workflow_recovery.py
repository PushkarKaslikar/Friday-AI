"""Unit tests for WorkflowEngine step recovery policy and strategy execution."""

from unittest.mock import MagicMock

from app.automation.workflow.action_registry import WorkflowActionRegistry
from app.automation.workflow.engine import WorkflowEngine
from app.automation.workflow.models import (
    ActionResult,
    ActionType,
    RecoveryPolicy,
    RecoveryStrategy,
    VerificationCondition,
    VerificationResult,
    VerificationType,
    WorkflowAction,
    WorkflowExecutionMode,
    WorkflowPlan,
    WorkflowState,
    WorkflowStep,
)
from app.automation.workflow.verifier_registry import StepVerifier


def test_recovery_strategy_execution():
    action_reg = MagicMock(spec=WorkflowActionRegistry)
    action_reg.has_handler.return_value = True
    action_reg.execute_action.return_value = ActionResult(
        status="SUCCESS", action_id="focus_window"
    )

    verifier = MagicMock(spec=StepVerifier)
    # Verification fails on 1st attempt, passes on 2nd attempt after recovery
    verifier.verify_condition.side_effect = [
        VerificationResult(
            status="FAILED",
            condition_type="WINDOW_FOCUSED",
            elapsed_ms=10.0,
            attempts=1,
            reason="Element stale",
        ),
        VerificationResult(
            status="PASSED",
            condition_type="WINDOW_FOCUSED",
            elapsed_ms=10.0,
            attempts=1,
            reason="Element recovered",
        ),
    ]

    engine = WorkflowEngine(action_registry=action_reg, step_verifier=verifier)

    plan = WorkflowPlan(
        name="Recovery Workflow",
        execution_mode=WorkflowExecutionMode.LIVE,
        steps=[
            WorkflowStep(
                order=1,
                name="Stale UI Step",
                action=WorkflowAction(action_type=ActionType.FOCUS_WINDOW),
                verification=VerificationCondition(
                    condition_type=VerificationType.WINDOW_FOCUSED
                ),
                recovery_policy=RecoveryPolicy(
                    strategy=RecoveryStrategy.RE_RESOLVE_TARGET, max_recovery_attempts=2
                ),
            )
        ],
    )

    res = engine.execute_workflow(plan)

    assert res.status == WorkflowState.COMPLETED
    assert res.recovery_count == 1
