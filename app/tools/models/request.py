"""Tool request specification model."""

import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.utilities.system_utils import get_timestamp_str


class ToolRequest(BaseModel):
    """Structured tool invocation request model."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_id: str = Field(description="Target tool identifier")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Input arguments payload"
    )
    timestamp: str = Field(default_factory=get_timestamp_str)
    context: dict[str, Any] = Field(
        default_factory=dict, description="Execution context metadata"
    )
