"""Structured Command model and lifecycle state machine."""

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.tools.base.risk import ToolRiskLevel
from app.utilities.system_utils import get_timestamp_str


class CommandSource(str, Enum):
    """Source origin for command instructions."""

    USER = "USER"
    AI = "AI"
    SYSTEM = "SYSTEM"
    SCHEDULED_TASK = "SCHEDULED_TASK"
    PLUGIN = "PLUGIN"


class CommandPriority(str, Enum):
    """Command priority levels."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CommandState(str, Enum):
    """Command lifecycle state machine transitions."""

    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    AUTHORIZED = "AUTHORIZED"
    QUEUED = "QUEUED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"
    REJECTED = "REJECTED"


VALID_TRANSITIONS: dict[CommandState, set[CommandState]] = {
    CommandState.CREATED: {
        CommandState.VALIDATING,
        CommandState.REJECTED,
        CommandState.CANCELLED,
    },
    CommandState.VALIDATING: {
        CommandState.AUTHORIZED,
        CommandState.REJECTED,
        CommandState.FAILED,
        CommandState.CANCELLED,
    },
    CommandState.AUTHORIZED: {
        CommandState.QUEUED,
        CommandState.EXECUTING,
        CommandState.REJECTED,
        CommandState.CANCELLED,
    },
    CommandState.QUEUED: {
        CommandState.EXECUTING,
        CommandState.CANCELLED,
        CommandState.TIMEOUT,
    },
    CommandState.EXECUTING: {
        CommandState.COMPLETED,
        CommandState.FAILED,
        CommandState.TIMEOUT,
        CommandState.CANCELLED,
    },
    CommandState.COMPLETED: set(),
    CommandState.FAILED: set(),
    CommandState.CANCELLED: set(),
    CommandState.TIMEOUT: set(),
    CommandState.REJECTED: set(),
}


class Command(BaseModel):
    """Strongly typed Command instruction model for Friday AI Assistant."""

    command_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique command ID"
    )
    tool_name: str = Field(description="Target tool identifier (e.g. system.echo)")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Structured arguments payload"
    )
    timestamp: str = Field(default_factory=get_timestamp_str)
    source: CommandSource = Field(
        default=CommandSource.USER, description="Command origin source"
    )
    priority: CommandPriority = Field(
        default=CommandPriority.NORMAL, description="Command execution priority"
    )
    timeout_seconds: float = Field(default=10.0, description="Execution timeout limit")
    execution_mode: str = Field(
        default="SYNC", description="Execution mode ('SYNC' or 'ASYNC')"
    )
    risk_level: ToolRiskLevel = Field(
        default=ToolRiskLevel.LOW, description="Security risk classification"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Context metadata"
    )
    correlation_id: str = Field(
        default="", description="Parent correlation tracking ID"
    )
    state: CommandState = Field(
        default=CommandState.CREATED, description="Current lifecycle state"
    )

    def transition_to(self, new_state: CommandState) -> bool:
        """Transition command state if valid per state machine rules.

        Args:
            new_state: Target CommandState enum value.

        Returns:
            bool: True if transition succeeded.

        Raises:
            ValueError: If state transition is invalid.
        """
        valid_next_states = VALID_TRANSITIONS.get(self.state, set())
        if new_state not in valid_next_states:
            raise ValueError(
                f"Invalid state transition from '{self.state.value}' to '{new_state.value}'."
            )
        self.state = new_state
        return True
