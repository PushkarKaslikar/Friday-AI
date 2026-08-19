"""Workflow Execution Automation Tool for Friday AI Assistant."""

from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory

if TYPE_CHECKING:
    from app.automation.workflow.workflow_controller import WorkflowManager


class WorkflowExecuteSequenceInput(BaseModel):
    plan: Any = Field(description="Structured WorkflowPlan specification or dictionary")
    mode: str | None = Field(
        default=None,
        description="Execution safety mode override (DRY_RUN, SIMULATE, LIVE)",
    )


class WorkflowExecuteSequenceTool(BaseTool):
    """Tool for executing multi-step verified automation workflow plans through WorkflowEngine."""

    def __init__(self, workflow_manager: Optional["WorkflowManager"] = None) -> None:
        metadata = ToolMetadata(
            tool_id="workflow.execute_sequence",
            name="WorkflowExecuteSequence",
            display_name="Execute Automation Workflow Plan",
            description="Validates and executes a structured multi-step computer automation plan through step-by-step state verification.",
            category=ToolCategory.WORKFLOW,
            tags=["workflow", "automation", "sequence", "verified"],
            input_schema=WorkflowExecuteSequenceInput,
            risk_level=ToolRiskLevel.HIGH,
            permissions=[ToolPermission.AUTOMATION_WORKFLOW],
            idempotent=False,
        )
        super().__init__(metadata)
        self.workflow_manager = workflow_manager

    def run_tool(
        self, validated_input: WorkflowExecuteSequenceInput, command_id: str = ""
    ) -> dict[str, Any]:
        raw_plan = validated_input.plan

        from app.automation.workflow.models import WorkflowExecutionMode, WorkflowPlan

        if isinstance(raw_plan, dict):
            plan = WorkflowPlan.model_validate(raw_plan)
        else:
            plan = raw_plan

        if validated_input.mode:
            plan.execution_mode = WorkflowExecutionMode(validated_input.mode.upper())

        if not self.workflow_manager:
            return {
                "status": "SUCCESS",
                "workflow_id": getattr(plan, "workflow_id", "wf_simulated_0"),
                "completed_steps": len(getattr(plan, "steps", [])),
                "execution_mode": (
                    plan.execution_mode.value
                    if hasattr(plan, "execution_mode")
                    else "SIMULATE"
                ),
                "simulated": True,
            }

        res = self.workflow_manager.execute_plan(plan)
        return {
            "status": (
                res.status.value if hasattr(res.status, "value") else str(res.status)
            ),
            "workflow_id": res.workflow_id,
            "completed_steps": res.completed_steps,
            "failed_step": res.failed_step,
            "duration_ms": res.duration_ms,
            "outputs": res.outputs,
            "verification_summary": res.verification_summary,
            "retry_count": res.retry_count,
            "recovery_count": res.recovery_count,
            "errors": res.errors,
        }
