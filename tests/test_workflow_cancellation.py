"""Unit tests for WorkflowEngine cancellation, user physical interruption, and mouse failsafe propagation."""

from unittest.mock import MagicMock

from app.automation.input.input_engine import InputEngine
from app.automation.workflow.engine import WorkflowEngine
from app.automation.workflow.examples import build_open_project_explorer_workflow
from app.automation.workflow.models import WorkflowExecutionMode, WorkflowState
from app.tools.execution.cancellation import CancellationToken


def test_workflow_cancellation_propagation():
    engine = WorkflowEngine()
    plan = build_open_project_explorer_workflow(mode=WorkflowExecutionMode.SIMULATE)
    token = CancellationToken()
    token.request_cancellation("User requested stop")

    res = engine.execute_workflow(plan, cancellation_token=token)

    assert res.status == WorkflowState.CANCELLED
    assert "cancelled" in res.errors[0].lower()


def test_user_interruption_event_handler():
    input_eng = MagicMock(spec=InputEngine)
    engine = WorkflowEngine(input_engine=input_eng)
    engine._active_live_workflow_id = "wf_live_1"

    engine._on_user_interruption_event(None)

    assert input_eng.release_all_inputs.called
    assert engine.get_workflow_state("wf_live_1") == WorkflowState.INTERRUPTED


def test_failsafe_event_handler():
    input_eng = MagicMock(spec=InputEngine)
    engine = WorkflowEngine(input_engine=input_eng)
    engine._active_live_workflow_id = "wf_live_2"

    engine._on_failsafe_event(None)

    assert input_eng.release_all_inputs.called
    assert engine.get_workflow_state("wf_live_2") == WorkflowState.ABORTED
