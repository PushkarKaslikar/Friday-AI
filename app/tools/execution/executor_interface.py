"""Abstract Tool Executor interface contract for tool execution engines."""

from abc import ABC, abstractmethod

from app.tools.models.command import Command
from app.tools.models.request import ToolRequest
from app.tools.models.result import ToolResult


class IToolExecutor(ABC):
    """Abstract interface contract for tool execution engine implementations."""

    @abstractmethod
    def execute_command(self, command: Command) -> ToolResult:
        """Execute structured Command model through registry lookup and validation."""

    @abstractmethod
    def execute_request(self, request: ToolRequest) -> ToolResult:
        """Execute raw ToolRequest model."""
