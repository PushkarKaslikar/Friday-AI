"""Unit tests for StepVerifier condition evaluation and operator composition."""

from app.automation.workflow.context import WorkflowExecutionContext
from app.automation.workflow.models import (
    VerificationCondition,
    VerificationOperator,
    VerificationType,
    WorkflowExecutionMode,
)
from app.automation.workflow.verifier_registry import StepVerifier


def test_step_verifier_none_condition_passes():
    verifier = StepVerifier()
    ctx = WorkflowExecutionContext(workflow_id="test_wf")

    res = verifier.verify_condition(None, ctx, mode=WorkflowExecutionMode.LIVE)
    assert res.status == "PASSED"


def test_step_verifier_simulate_mode_passes():
    verifier = StepVerifier()
    ctx = WorkflowExecutionContext(workflow_id="test_wf")
    cond = VerificationCondition(
        condition_type=VerificationType.FOLDER_EXISTS, target="D:\\Friday AI"
    )

    res = verifier.verify_condition(cond, ctx, mode=WorkflowExecutionMode.SIMULATE)
    assert res.status == "PASSED"


def test_step_verifier_all_operator_composition():
    verifier = StepVerifier()
    ctx = WorkflowExecutionContext(workflow_id="test_wf")

    cond1 = VerificationCondition(
        condition_type=VerificationType.FOLDER_EXISTS, target="D:\\Friday AI"
    )
    cond2 = VerificationCondition(
        condition_type=VerificationType.FOLDER_EXISTS, target="D:\\Friday AI"
    )

    composite = VerificationCondition(
        operator=VerificationOperator.ALL,
        sub_conditions=[cond1, cond2],
    )

    res = verifier.verify_condition(composite, ctx, mode=WorkflowExecutionMode.SIMULATE)
    assert res.status == "PASSED"
