"""Tool metadata Pydantic model for schema validation and discovery."""

from pydantic import BaseModel, Field

from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.categories import ToolCategory


class ToolMetadata(BaseModel):
    """Strongly typed metadata specification for Friday AI tools."""

    tool_id: str = Field(
        description="Unique machine-readable tool ID (e.g. system.echo)"
    )
    name: str = Field(description="System identifier name")
    display_name: str = Field(description="Human-readable title display name")
    description: str = Field(
        description="Detailed tool description for AI tool selection"
    )
    version: str = Field(default="1.0.0", description="Tool version string")
    author: str = Field(
        default="Friday AI Team", description="Author or plugin provider"
    )
    category: ToolCategory = Field(
        default=ToolCategory.SYSTEM, description="Tool category classification"
    )
    tags: list[str] = Field(
        default_factory=list, description="Search and discovery tags"
    )

    input_schema: type[BaseModel] | None = Field(
        default=None, description="Pydantic model class for inputs"
    )
    output_schema: type[BaseModel] | None = Field(
        default=None, description="Pydantic model class for outputs"
    )

    risk_level: ToolRiskLevel = Field(
        default=ToolRiskLevel.LOW, description="Security risk classification"
    )
    permissions: list[ToolPermission] = Field(
        default_factory=list, description="Required permission capabilities"
    )
    confirmation_required: bool = Field(
        default=False, description="Whether explicit user confirmation is needed"
    )

    is_enabled: bool = Field(default=True, description="Active tool enabled flag")
    timeout_seconds: float = Field(
        default=10.0, description="Execution timeout limit in seconds"
    )
    retryable: bool = Field(
        default=False, description="Whether execution can be retried on failure"
    )
    max_retries: int = Field(default=0, description="Maximum retry count if retryable")
    idempotent: bool = Field(
        default=False,
        description="Whether tool execution is side-effect-free / idempotent",
    )
    platform_compatibility: list[str] = Field(
        default_factory=lambda: ["Windows"], description="Supported OS platforms"
    )

    model_config = {"arbitrary_types_allowed": True}
