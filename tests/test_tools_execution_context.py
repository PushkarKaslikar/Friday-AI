"""Unit tests for ExecutionContext and CancellationToken."""

import pytest

from app.tools.execution.cancellation import CancellationToken
from app.tools.execution.execution_context import ExecutionContext


def test_cancellation_token():
    token = CancellationToken()
    assert token.is_cancelled is False

    token.request_cancellation("Test cancellation")
    assert token.is_cancelled is True
    assert token.reason == "Test cancellation"

    with pytest.raises(RuntimeError, match="Operation cancelled: Test cancellation"):
        token.throw_if_cancelled()


def test_execution_context_defaults():
    context = ExecutionContext(tool_id="system.echo")
    assert context.execution_id.startswith("exec_")
    assert context.tool_id == "system.echo"
    assert context.timeout_seconds == 10.0
    assert context.retry_attempt == 0
