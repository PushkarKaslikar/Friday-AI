"""Unit tests for Command model and state machine transitions."""

import pytest

from app.tools.models.command import (
    Command,
    CommandPriority,
    CommandSource,
    CommandState,
)


def test_command_creation():
    cmd = Command(
        tool_name="system.echo",
        arguments={"message": "hello"},
        source=CommandSource.USER,
        priority=CommandPriority.HIGH,
    )
    assert cmd.command_id != ""
    assert cmd.tool_name == "system.echo"
    assert cmd.arguments == {"message": "hello"}
    assert cmd.source == CommandSource.USER
    assert cmd.priority == CommandPriority.HIGH
    assert cmd.state == CommandState.CREATED


def test_command_valid_state_transitions():
    cmd = Command(tool_name="system.echo")
    assert cmd.state == CommandState.CREATED

    assert cmd.transition_to(CommandState.VALIDATING) is True
    assert cmd.state == CommandState.VALIDATING

    assert cmd.transition_to(CommandState.AUTHORIZED) is True
    assert cmd.state == CommandState.AUTHORIZED

    assert cmd.transition_to(CommandState.EXECUTING) is True
    assert cmd.state == CommandState.EXECUTING

    assert cmd.transition_to(CommandState.COMPLETED) is True
    assert cmd.state == CommandState.COMPLETED


def test_command_invalid_state_transition_raises():
    cmd = Command(tool_name="system.echo")
    assert cmd.state == CommandState.CREATED

    # Cannot transition directly from CREATED to COMPLETED
    with pytest.raises(ValueError, match="Invalid state transition"):
        cmd.transition_to(CommandState.COMPLETED)
