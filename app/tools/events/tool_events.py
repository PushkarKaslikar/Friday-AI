"""Typed EventBus models for tool events."""

from dataclasses import dataclass

from app.services.events.event_models import Event


@dataclass
class ToolRegistered(Event):
    """Event published when a tool is registered in ToolRegistry."""

    tool_id: str = ""
    name: str = ""
    category: str = ""


@dataclass
class ToolEnabled(Event):
    """Event published when a tool is enabled."""

    tool_id: str = ""


@dataclass
class ToolDisabled(Event):
    """Event published when a tool is disabled."""

    tool_id: str = ""


@dataclass
class ToolExecutionStarted(Event):
    """Event published when tool execution starts."""

    tool_id: str = ""
    command_id: str = ""
    execution_id: str = ""


@dataclass
class ToolExecutionCompleted(Event):
    """Event published when tool execution completes successfully."""

    tool_id: str = ""
    command_id: str = ""
    execution_id: str = ""
    duration_seconds: float = 0.0


@dataclass
class ToolExecutionFailed(Event):
    """Event published when tool execution fails."""

    tool_id: str = ""
    command_id: str = ""
    error_message: str = ""
    error_code: str = "EXECUTION_FAILED"


@dataclass
class ToolExecutionCancelled(Event):
    """Event published when tool execution is cancelled."""

    tool_id: str = ""
    command_id: str = ""


@dataclass
class ToolExecutionTimedOut(Event):
    """Event published when tool execution times out."""

    tool_id: str = ""
    command_id: str = ""
    execution_id: str = ""
    timeout_seconds: float = 0.0


@dataclass
class ToolExecutionAuthorizationRequired(Event):
    """Event published when tool execution requires explicit user authorization."""

    tool_id: str = ""
    command_id: str = ""
    execution_id: str = ""
    risk_level: str = "LOW"


@dataclass
class ToolExecutionAuthorizationDenied(Event):
    """Event published when authorization is denied for a tool execution."""

    tool_id: str = ""
    command_id: str = ""
    execution_id: str = ""
    reason: str = "Permission denied"


@dataclass
class ToolExecutionRetrying(Event):
    """Event published when a tool execution attempt fails and is being retried."""

    tool_id: str = ""
    command_id: str = ""
    execution_id: str = ""
    attempt: int = 1
    max_retries: int = 1


@dataclass
class ToolHealthChanged(Event):
    """Event published when a tool's health status changes."""

    tool_id: str = ""
    status: str = ""
    message: str = ""
