"""Unit tests for WorkflowEngine execution loop, state machine transitions, and variable resolution."""

from app.automation.workflow.engine import WorkflowEngine
from app.automation.workflow.examples import (
    build_arrange_workspace_workflow,
    build_open_project_explorer_workflow,
    build_open_project_terminal_workflow,
)
from app.automation.workflow.models import (
    WorkflowExecutionMode,
    WorkflowState,
)


def test_workflow_engine_simulate_execution():
    engine = WorkflowEngine()
    plan = build_open_project_explorer_workflow(mode=WorkflowExecutionMode.SIMULATE)

    result = engine.execute_workflow(plan)

    assert result.status == WorkflowState.COMPLETED
    assert result.completed_steps == 4
    assert len(result.step_results) == 4
    assert result.outputs.get("project_path") == "D:\\Friday AI"


def test_workflow_engine_dry_run_execution():
    engine = WorkflowEngine()
    plan = build_open_project_terminal_workflow(mode=WorkflowExecutionMode.DRY_RUN)

    result = engine.execute_workflow(plan)

    assert result.status == WorkflowState.COMPLETED
    assert result.completed_steps == 4


def test_workflow_engine_arrange_workspace_example():
    engine = WorkflowEngine()
    plan = build_arrange_workspace_workflow(mode=WorkflowExecutionMode.SIMULATE)

    result = engine.execute_workflow(plan)

    assert result.status == WorkflowState.COMPLETED
    assert result.completed_steps == 3
