"""Tool health monitoring models."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.utilities.system_utils import get_timestamp_str


class ToolHealthStatus(str, Enum):
    """Tool health status enum."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class ToolHealthReport(BaseModel):
    """Diagnostic health report for a registered tool."""

    tool_id: str
    status: ToolHealthStatus = ToolHealthStatus.HEALTHY
    message: str = "Tool operating normally."
    last_check: str = Field(default_factory=get_timestamp_str)
    metrics: dict[str, Any] = Field(default_factory=dict)
