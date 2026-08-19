"""Unit tests for WorkflowEngine security boundaries, variable resolution safety, and single LIVE workflow resource locking."""

import pytest

from app.automation.workflow.context import WorkflowExecutionContext
from app.automation.workflow.engine import WorkflowEngine
from app.automation.workflow.errors import (
    ResourceBusyError,
    VariableInvalidError,
)
from app.automation.workflow.models import (
    ActionType,
    WorkflowAction,
    WorkflowExecutionMode,
    WorkflowPlan,
    WorkflowStep,
)


def test_context_variable_safety_rejects_code_injection():
    ctx = WorkflowExecutionContext(workflow_id="wf_sec")
    with pytest.raises(VariableInvalidError, match="Invalid variable name syntax"):
        ctx.set_variable("bad_name; eval('os.system')", "value")


def test_context_template_substitution():
    ctx = WorkflowExecutionContext(
        workflow_id="wf_sec", initial_variables={"project_path": "D:\\Friday AI"}
    )
    resolved = ctx.resolve_value("{project_path}\\src")
    assert resolved == "D:\\Friday AI\\src"


def test_resource_busy_lock_prevents_concurrent_live_workflows():
    engine = WorkflowEngine()
    engine._active_live_workflow_id = "wf_live_active"

    plan = WorkflowPlan(
        workflow_id="wf_live_conflicting",
        name="Conflicting Live Workflow",
        execution_mode=WorkflowExecutionMode.LIVE,
        steps=[
            WorkflowStep(
                order=1,
                name="Step 1",
                action=WorkflowAction(action_type=ActionType.LAUNCH_APP, target="cmd"),
            )
        ],
    )

    with pytest.raises(ResourceBusyError, match="is currently executing"):
        engine.execute_workflow(plan)
