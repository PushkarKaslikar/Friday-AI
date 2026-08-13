"""Application Info Tool providing application metadata."""

from pydantic import BaseModel, Field

from app.platform.identity.app_identity import APP_IDENTITY
from app.tools.base.metadata import ToolMetadata
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory


class AppInfoInput(BaseModel):
    """Input payload for ApplicationInfoTool."""

    include_build_details: bool = Field(
        default=True, description="Whether to include build info details"
    )


class ApplicationInfoTool(BaseTool):
    """Safe test tool querying application identity metadata."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="system.get_application_info",
            name="application_info_tool",
            display_name="Get Application Info Tool",
            description="Queries application metadata, name, version, and build info.",
            version="1.0.0",
            category=ToolCategory.SYSTEM,
            tags=["info", "metadata", "system", "version"],
            input_schema=AppInfoInput,
            risk_level=ToolRiskLevel.LOW,
            confirmation_required=False,
            idempotent=True,
        )
        super().__init__(metadata=meta)

    def run_tool(self, validated_input: BaseModel, command_id: str = "") -> dict:
        """Query application identity."""
        inp: AppInfoInput = validated_input  # type: ignore
        info = {
            "name": APP_IDENTITY.name,
            "version": APP_IDENTITY.version,
            "environment": APP_IDENTITY.environment,
        }
        if inp.include_build_details:
            info["company"] = APP_IDENTITY.company
            info["author"] = APP_IDENTITY.author
            info["build_date"] = APP_IDENTITY.build_date
            info["build_number"] = APP_IDENTITY.build_number
        return info
