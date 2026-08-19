"""Unit tests for WorkflowExecuteSequenceTool validation and execution."""

from app.automation.workflow.examples import build_open_project_explorer_workflow
from app.automation.workflow.models import WorkflowExecutionMode
from app.automation.workflow.workflow_controller import WorkflowManager
from app.tools.builtin.automation.workflow_tools import WorkflowExecuteSequenceTool


def test_workflow_tool_execution_simulate():
    wf_mgr = WorkflowManager()
    tool = WorkflowExecuteSequenceTool(workflow_manager=wf_mgr)

    plan = build_open_project_explorer_workflow(mode=WorkflowExecutionMode.SIMULATE)
    res = tool.execute({"plan": plan.model_dump()})

    assert res.success
    assert res.data["status"] == "COMPLETED"
    assert res.data["completed_steps"] == 4
