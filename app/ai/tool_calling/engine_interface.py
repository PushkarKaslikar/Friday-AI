"""Abstract boundary contract for Tool Calling & Function Binding Engine.

Phase 4.3 - Tool Calling & Function Binding Engine
"""

from abc import ABC, abstractmethod
from typing import Any

from app.ai.tool_calling.models import (
    ToolCall,
    ToolCallingConfiguration,
    ToolCallResult,
    ToolCallStatus,
    ToolDefinition,
)
from app.tools.execution.execution_context import ExecutionContext


class IToolCallingEngine(ABC):
    """Abstract interface contract for Tool Calling & Function Binding Engine."""

    @abstractmethod
    def get_tool_definitions(
        self, query: str | None = None, category: str | None = None, max_tools: int = 10
    ) -> list[ToolDefinition]:
        """Retrieve model-friendly ToolDefinition schemas matching optional query or category."""

    @abstractmethod
    def parse_tool_call(self, provider_output: Any) -> ToolCall | None:
        """Parse raw model response payload into canonical ToolCall model."""

    @abstractmethod
    def validate_tool_call(
        self, call: ToolCall
    ) -> tuple[bool, ToolCallStatus, str | None]:
        """Validate tool existence, enabled state, required arguments, and types."""

    @abstractmethod
    def execute_tool_call(
        self, call: ToolCall, context: ExecutionContext | None = None
    ) -> ToolCallResult:
        """Validate and delegate tool execution to Phase 2 ToolExecutor engine."""

    @abstractmethod
    def execute_multiple_tool_calls(
        self, calls: list[ToolCall], sequential: bool = True
    ) -> list[ToolCallResult]:
        """Execute sequence of multiple tool calls."""

    @property
    @abstractmethod
    def config(self) -> ToolCallingConfiguration:
        """Return active engine configuration settings."""
