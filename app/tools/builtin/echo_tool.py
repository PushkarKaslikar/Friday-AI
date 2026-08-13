"""Echo Tool for validating tool input validation, execution, and output serialization."""

from pydantic import BaseModel, Field

from app.tools.base.metadata import ToolMetadata
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory


class EchoInput(BaseModel):
    """Input arguments for EchoTool."""

    message: str = Field(description="Message text to echo back")
    repeat: int = Field(default=1, ge=1, le=10, description="Repeat count (1 to 10)")


class EchoOutput(BaseModel):
    """Output result schema for EchoTool."""

    echoed_text: str = Field(description="Resulting echoed text")
    length: int = Field(description="Total character length")


class EchoTool(BaseTool):
    """Safe test tool echoing input messages."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="system.echo",
            name="echo_tool",
            display_name="Echo Message Tool",
            description="Safely echoes back input text message for testing tool framework contracts.",
            version="1.0.0",
            category=ToolCategory.SYSTEM,
            tags=["test", "echo", "utility", "system"],
            input_schema=EchoInput,
            output_schema=EchoOutput,
            risk_level=ToolRiskLevel.LOW,
            confirmation_required=False,
            idempotent=True,
        )
        super().__init__(metadata=meta)

    def run_tool(self, validated_input: BaseModel, command_id: str = "") -> dict:
        """Execute echo logic."""
        inp: EchoInput = validated_input  # type: ignore
        result_text = " ".join([inp.message] * inp.repeat)
        return {"echoed_text": result_text, "length": len(result_text)}
