"""Domain models and data structures for Tool Calling & Function Binding Engine.

Phase 4.3 - Tool Calling & Function Binding Engine
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolCallStatus(str, Enum):
    """Execution and validation status of a tool call."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    INVALID_ARGUMENTS = "INVALID_ARGUMENTS"
    AUTHORIZATION_REQUIRED = "AUTHORIZATION_REQUIRED"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


@dataclass
class ToolDefinition:
    """Canonical model-friendly schema definition for a tool."""

    tool_name: str
    description: str
    category: str = "SYSTEM"
    parameters_schema: dict[str, Any] = field(default_factory=dict)
    required_parameters: list[str] = field(default_factory=list)
    risk_level: str = "LOW"
    permissions: list[str] = field(default_factory=list)
    confirmation_required: bool = False
    is_enabled: bool = True
    version: str = "1.0.0"


@dataclass
class ToolCall:
    """Canonical internal model representation of an LLM tool call request."""

    call_id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    raw_provider_payload: dict[str, Any] | None = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolCallResult:
    """Structured result returned after tool call validation and execution."""

    call_id: str
    tool_name: str
    status: ToolCallStatus
    result: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: float = 0.0
    sanitized_result: dict[str, Any] | None = None
    execution_id: str | None = None
    model_facing_output: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolCallingConfiguration:
    """Configuration settings for Tool Calling Engine."""

    enabled: bool = True
    max_tool_definitions: int = 20
    max_result_chars: int = 4000
    duplicate_call_protection: bool = True
    schema_cache_enabled: bool = True
