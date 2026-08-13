"""EventBus typed events for Tool Calling & Function Binding Engine.

Phase 4.3 - Tool Calling & Function Binding Engine
"""

import time
from dataclasses import dataclass, field

from app.services.events.event_models import Event


@dataclass
class ToolCallGenerated(Event):
    """Event published when LLM produces a raw tool call."""

    call_id: str = ""
    tool_name: str = ""
    arguments: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ToolCallGenerated", init=False)


@dataclass
class ToolCallValidated(Event):
    """Event published when a tool call passes schema and security validation."""

    call_id: str = ""
    tool_name: str = ""
    is_valid: bool = True
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ToolCallValidated", init=False)


@dataclass
class ToolCallRejected(Event):
    """Event published when a tool call fails validation or authorization."""

    call_id: str = ""
    tool_name: str = ""
    reason: str = ""
    status: str = "REJECTED"
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ToolCallRejected", init=False)


@dataclass
class ToolCallExecutionStarted(Event):
    """Event published when ToolCallingEngine delegates tool call to Phase 2 ToolExecutor."""

    call_id: str = ""
    tool_name: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ToolCallExecutionStarted", init=False)


@dataclass
class ToolCallExecutionCompleted(Event):
    """Event published when tool call execution succeeds."""

    call_id: str = ""
    tool_name: str = ""
    status: str = "SUCCESS"
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ToolCallExecutionCompleted", init=False)


@dataclass
class ToolCallExecutionFailed(Event):
    """Event published when tool call execution fails."""

    call_id: str = ""
    tool_name: str = ""
    error_message: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ToolCallExecutionFailed", init=False)
