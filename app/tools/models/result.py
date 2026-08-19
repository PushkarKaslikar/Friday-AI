"""Standardized Tool Result payload model."""

import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.tools.models.errors import ToolErrorCode
from app.utilities.system_utils import get_timestamp_str


class ToolResult(BaseModel):
    """Standardized tool execution result object returned by all tools."""

    success: bool = Field(description="Execution success flag")
    tool_id: str = Field(description="Unique tool identifier")
    command_id: str = Field(default="", description="Associated command ID")
    execution_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique execution UUID"
    )

    result_data: Any = Field(
        default=None, description="Structured result data returned by tool"
    )
    error: str | None = Field(
        default=None, description="Error message if execution failed"
    )
    error_code: ToolErrorCode | None = Field(
        default=None, description="Standardized error code classification"
    )

    execution_duration: float = Field(default=0.0, description="Duration in seconds")
    timestamp: str = Field(default_factory=get_timestamp_str)
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional context metadata"
    )

    @property
    def is_success(self) -> bool:
        """Alias for success attribute."""
        return self.success

    @property
    def data(self) -> Any:
        """Alias for result_data attribute."""
        return self.result_data

    @property
    def result(self) -> Any:
        """Alias for result_data attribute."""
        return self.result_data

    @property
    def result_id(self) -> str:
        """Alias for execution_id attribute."""
        return self.execution_id

    @classmethod
    def ok(
        cls,
        tool_id: str,
        result_data: Any,
        command_id: str = "",
        execution_duration: float = 0.0,
    ) -> "ToolResult":
        """Factory method for successful ToolResult."""
        return cls(
            success=True,
            tool_id=tool_id,
            command_id=command_id,
            result_data=result_data,
            execution_duration=execution_duration,
        )

    @classmethod
    def fail(
        cls,
        tool_id: str,
        error: str,
        error_code: ToolErrorCode = ToolErrorCode.EXECUTION_FAILED,
        command_id: str = "",
        execution_duration: float = 0.0,
    ) -> "ToolResult":
        """Factory method for failed ToolResult."""
        return cls(
            success=False,
            tool_id=tool_id,
            command_id=command_id,
            error=error,
            error_code=error_code,
            execution_duration=execution_duration,
        )
