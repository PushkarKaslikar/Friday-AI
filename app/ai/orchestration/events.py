"""EventBus typed events for AI Orchestrator & Reasoning Engine.

Phase 4.2 - AI Orchestrator & Reasoning Workflow Engine
"""

import time
from dataclasses import dataclass, field

from app.services.events.event_models import Event


@dataclass
class OrchestrationStarted(Event):
    """Event published when request orchestration begins."""

    request_id: str = ""
    user_input: str = ""
    session_id: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="OrchestrationStarted", init=False)


@dataclass
class ActionPlanCreated(Event):
    """Event published when an action plan is formulated."""

    request_id: str = ""
    plan_id: str = ""
    step_count: int = 0
    required_tools: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ActionPlanCreated", init=False)


@dataclass
class ToolExecutionRequested(Event):
    """Event published when orchestrator requests tool execution."""

    request_id: str = ""
    tool_name: str = ""
    arguments: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ToolExecutionRequested", init=False)


@dataclass
class ToolExecutionReturned(Event):
    """Event published when requested tool execution completes."""

    request_id: str = ""
    tool_name: str = ""
    status: str = "SUCCESS"
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ToolExecutionReturned", init=False)


@dataclass
class OrchestrationCompleted(Event):
    """Event published when request orchestration successfully finishes."""

    request_id: str = ""
    success: bool = True
    tool_count: int = 0
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="OrchestrationCompleted", init=False)


@dataclass
class OrchestrationFailed(Event):
    """Event published when request orchestration fails."""

    request_id: str = ""
    error_message: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="OrchestrationFailed", init=False)
