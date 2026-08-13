"""Retry policy evaluator enforcing idempotent retry rules and error constraints."""

from app.tools.base.metadata import ToolMetadata
from app.tools.models.errors import ToolErrorCode

UNRETRYABLE_ERROR_CODES: set[ToolErrorCode] = {
    ToolErrorCode.INVALID_INPUT,
    ToolErrorCode.PERMISSION_DENIED,
    ToolErrorCode.AUTHORIZATION_REQUIRED,
    ToolErrorCode.CANCELLED,
    ToolErrorCode.PLATFORM_UNSUPPORTED,
}


class RetryPolicy:
    """Evaluates whether a failed tool execution attempt is eligible for retry."""

    @staticmethod
    def should_retry(
        metadata: ToolMetadata,
        error_code: ToolErrorCode | None,
        current_attempt: int,
    ) -> bool:
        """Evaluate whether retry is allowed.

        Args:
            metadata: Tool metadata specification.
            error_code: Error code from failed execution.
            current_attempt: 0-indexed current retry count.

        Returns:
            bool: True if execution can be retried.
        """
        if not metadata.retryable:
            return False

        if current_attempt >= metadata.max_retries:
            return False

        if not metadata.idempotent:
            return False

        return error_code not in UNRETRYABLE_ERROR_CODES
