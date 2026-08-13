"""Standardized tool error codes and exception classes."""

from enum import Enum


class ToolErrorCode(str, Enum):
    """Standardized tool error code classification."""

    INVALID_INPUT = "INVALID_INPUT"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_DISABLED = "TOOL_DISABLED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    AUTHORIZATION_REQUIRED = "AUTHORIZATION_REQUIRED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    PLATFORM_UNSUPPORTED = "PLATFORM_UNSUPPORTED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ToolExecutionError(Exception):
    """Structured exception raised during tool payload execution or validation."""

    def __init__(
        self,
        error_code: ToolErrorCode,
        message: str,
        tool_id: str = "",
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.tool_id = tool_id
        self.details = details or {}
