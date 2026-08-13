"""Strongly typed ExecutionContext model for correlation across pipeline stages."""

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.execution.cancellation import CancellationToken
from app.tools.models.command import CommandSource, CommandState
from app.utilities.system_utils import get_timestamp_str


@dataclass
class ExecutionContext:
    """Correlation context carried through all stages of tool execution."""

    execution_id: str = field(default_factory=lambda: f"exec_{uuid.uuid4().hex[:12]}")
    command_id: str = ""
    tool_id: str = ""
    request_id: str = ""
    correlation_id: str = ""

    source: CommandSource = CommandSource.USER
    risk_level: ToolRiskLevel = ToolRiskLevel.LOW
    granted_permissions: set[ToolPermission] = field(default_factory=set)

    timeout_seconds: float = 10.0
    cancellation_token: CancellationToken = field(default_factory=CancellationToken)

    retry_attempt: int = 0
    max_retries: int = 0

    state: CommandState = CommandState.CREATED
    start_time: str = field(default_factory=get_timestamp_str)
    metadata: dict[str, Any] = field(default_factory=dict)
