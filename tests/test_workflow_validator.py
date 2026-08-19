"""Unit tests for WorkflowValidator plan validation rules."""

import pytest

from app.automation.workflow.errors import WorkflowInvalidError
from app.automation.workflow.models import (
    ActionType,
    VerificationCondition,
    VerificationType,
    WorkflowAction,
    WorkflowExecutionMode,
    WorkflowPlan,
    WorkflowStep,
)
from app.automation.workflow.validator import WorkflowValidator


def test_validator_accepts_valid_plan():
    validator = WorkflowValidator()
    plan = WorkflowPlan(
        name="Valid Plan",
        execution_mode=WorkflowExecutionMode.SIMULATE,
        steps=[
            WorkflowStep(
                order=1,
                name="Step 1",
                action=WorkflowAction(
                    action_type=ActionType.LAUNCH_APP, target="explorer"
                ),
                verification=VerificationCondition(
                    condition_type=VerificationType.PROCESS_RUNNING, target="explorer"
                ),
            )
        ],
    )
    assert validator.validate_plan(plan) is True


def test_validator_rejects_empty_steps():
    validator = WorkflowValidator()
    plan = WorkflowPlan(name="Empty Plan", steps=[])
    with pytest.raises(WorkflowInvalidError, match="contains no steps"):
        validator.validate_plan(plan)


def test_validator_rejects_duplicate_step_orders():
    validator = WorkflowValidator()
    step1 = WorkflowStep(
        order=1, name="Step 1", action=WorkflowAction(action_type=ActionType.LAUNCH_APP)
    )
    step2 = WorkflowStep(
        order=1, name="Step 2", action=WorkflowAction(action_type=ActionType.LAUNCH_APP)
    )
    plan = WorkflowPlan(name="Duplicate Orders", steps=[step1, step2])
    with pytest.raises(WorkflowInvalidError, match="Duplicate step orders"):
        validator.validate_plan(plan)
