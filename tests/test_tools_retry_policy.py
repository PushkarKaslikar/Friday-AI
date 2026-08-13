"""Unit tests for RetryPolicy rules evaluation."""

from app.tools.base.metadata import ToolMetadata
from app.tools.execution.retry_policy import RetryPolicy
from app.tools.models.errors import ToolErrorCode


def test_retry_policy_evaluation():
    meta_retryable = ToolMetadata(
        tool_id="system.echo",
        name="echo",
        display_name="Echo",
        description="Echo",
        retryable=True,
        max_retries=2,
        idempotent=True,
    )

    # Allowed retry
    assert (
        RetryPolicy.should_retry(meta_retryable, ToolErrorCode.EXECUTION_FAILED, 0)
        is True
    )

    # Exceeded max retries
    assert (
        RetryPolicy.should_retry(meta_retryable, ToolErrorCode.EXECUTION_FAILED, 2)
        is False
    )

    # Unretryable error code
    assert (
        RetryPolicy.should_retry(meta_retryable, ToolErrorCode.INVALID_INPUT, 0)
        is False
    )
    assert (
        RetryPolicy.should_retry(meta_retryable, ToolErrorCode.PERMISSION_DENIED, 0)
        is False
    )

    # Non-idempotent tool
    meta_non_idempotent = ToolMetadata(
        tool_id="system.echo",
        name="echo",
        display_name="Echo",
        description="Echo",
        retryable=True,
        max_retries=2,
        idempotent=False,
    )
    assert (
        RetryPolicy.should_retry(meta_non_idempotent, ToolErrorCode.EXECUTION_FAILED, 0)
        is False
    )
