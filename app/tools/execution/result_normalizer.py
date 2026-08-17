"""Result Normalizer and Sensitive Data Sanitizer."""

from typing import Any

from pydantic import ValidationError

from app.tools.models.errors import ToolErrorCode, ToolExecutionError
from app.tools.models.result import ToolResult

SENSITIVE_KEYS: set[str] = {
    "password",
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "private_key",
    "passphrase",
}


class SensitiveDataSanitizer:
    """Recursively masks sensitive fields in dictionaries or dictionaries of parameters."""

    @classmethod
    def sanitize(cls, data: Any) -> Any:
        """Sanitize sensitive dictionary entries.

        Args:
            data: Arbitrary object data.

        Returns:
            Sanitized object with sensitive key values masked as '********'.
        """
        if isinstance(data, dict):
            sanitized = {}
            for key, val in data.items():
                if any(s_key in key.lower() for s_key in SENSITIVE_KEYS):
                    sanitized[key] = "********"
                else:
                    sanitized[key] = cls.sanitize(val)
            return sanitized
        if isinstance(data, list):
            return [cls.sanitize(item) for item in data]
        return data

    @classmethod
    def contains_sensitive_data(cls, text: str) -> bool:
        """Check whether a text string contains sensitive keys or credential patterns."""
        if not text or not isinstance(text, str):
            return False
        text_lower = text.lower()
        return any(s_key in text_lower for s_key in SENSITIVE_KEYS)


class ResultNormalizer:
    """Normalizes raw tool output values or exceptions into standardized ToolResult models."""

    @classmethod
    def normalize_exception(
        cls,
        tool_id: str,
        command_id: str,
        exc: Exception,
        duration: float = 0.0,
    ) -> ToolResult:
        """Map exception instance to standardized ToolResult error format.

        Args:
            tool_id: Target tool ID.
            command_id: Command correlation ID.
            exc: Exception raised during execution.
            duration: Duration in seconds.

        Returns:
            ToolResult: Standardized failure ToolResult model.
        """
        if isinstance(exc, ToolExecutionError):
            return ToolResult.fail(
                tool_id=tool_id,
                command_id=command_id,
                error=exc.message,
                error_code=exc.error_code,
                execution_duration=duration,
            )

        if isinstance(exc, ValidationError):
            return ToolResult.fail(
                tool_id=tool_id,
                command_id=command_id,
                error=f"Input validation error: {exc}",
                error_code=ToolErrorCode.INVALID_INPUT,
                execution_duration=duration,
            )

        if isinstance(exc, PermissionError):
            return ToolResult.fail(
                tool_id=tool_id,
                command_id=command_id,
                error=f"Permission denied: {exc}",
                error_code=ToolErrorCode.PERMISSION_DENIED,
                execution_duration=duration,
            )

        if isinstance(exc, TimeoutError):
            return ToolResult.fail(
                tool_id=tool_id,
                command_id=command_id,
                error=f"Execution timed out: {exc}",
                error_code=ToolErrorCode.TIMEOUT,
                execution_duration=duration,
            )

        if isinstance(exc, RuntimeError) and "cancelled" in str(exc).lower():
            return ToolResult.fail(
                tool_id=tool_id,
                command_id=command_id,
                error=str(exc),
                error_code=ToolErrorCode.CANCELLED,
                execution_duration=duration,
            )

        return ToolResult.fail(
            tool_id=tool_id,
            command_id=command_id,
            error=f"Internal error: {exc}",
            error_code=ToolErrorCode.INTERNAL_ERROR,
            execution_duration=duration,
        )
