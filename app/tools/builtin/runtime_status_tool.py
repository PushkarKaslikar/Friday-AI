"""Runtime Status Tool providing service engine diagnostic statistics."""

from pydantic import BaseModel, Field

from app.services.core.service_manager import ServiceManager
from app.tools.base.metadata import ToolMetadata
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory


class RuntimeStatusInput(BaseModel):
    """Input payload for RuntimeStatusTool."""

    include_services: bool = Field(
        default=True, description="Whether to include registered services summary"
    )


class RuntimeStatusTool(BaseTool):
    """Safe test tool querying runtime status statistics."""

    def __init__(self, service_manager: ServiceManager | None = None) -> None:
        meta = ToolMetadata(
            tool_id="system.get_runtime_status",
            name="runtime_status_tool",
            display_name="Get Runtime Status Tool",
            description="Queries background service engine status and service health state.",
            version="1.0.0",
            category=ToolCategory.SYSTEM,
            tags=["status", "runtime", "health", "system"],
            input_schema=RuntimeStatusInput,
            risk_level=ToolRiskLevel.LOW,
            confirmation_required=False,
            idempotent=True,
        )
        super().__init__(metadata=meta)
        self.service_manager = service_manager or ServiceManager()

    def run_tool(self, validated_input: BaseModel, command_id: str = "") -> dict:
        """Query runtime status."""
        inp: RuntimeStatusInput = validated_input  # type: ignore
        summary = (
            self.service_manager.get_status_summary() if inp.include_services else {}
        )
        return {
            "status": "RUNNING",
            "services_count": len(summary),
            "services": summary,
        }
