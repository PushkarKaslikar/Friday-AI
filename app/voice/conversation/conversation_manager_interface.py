"""Abstract interface contract for Conversation Manager.

Phase 3.8 - Conversation Manager, Session Context & Short-Term Memory
"""

from abc import ABC, abstractmethod
from typing import Any

from app.voice.conversation.manager_models import (
    ContextSnapshot,
    ConversationManagerConfiguration,
    ConversationTurn,
    ReferenceResolutionResult,
    TrackedEntity,
)


class IConversationManager(ABC):
    """Abstract interface contract for Conversation Manager & Short-Term Memory."""

    @abstractmethod
    def start_session(
        self, session_id: str, activation_source: str = "WAKE_WORD"
    ) -> None:
        """Initialize short-term session context for active conversation session."""

    @abstractmethod
    def end_session(self, session_id: str, reason: str = "normal_completion") -> None:
        """Flush and finalize short-term session context."""

    @abstractmethod
    def add_user_turn(
        self, session_id: str, text: str, turn_number: int
    ) -> ConversationTurn:
        """Add user transcript turn to short-term memory."""

    @abstractmethod
    def add_assistant_turn(
        self, session_id: str, text: str, turn_number: int
    ) -> ConversationTurn:
        """Add assistant response turn to short-term memory."""

    @abstractmethod
    def track_entity(self, session_id: str, entity: TrackedEntity) -> None:
        """Track entity in active session context."""

    @abstractmethod
    def resolve_reference(
        self, session_id: str, user_input: str
    ) -> ReferenceResolutionResult:
        """Resolve entity reference ("it", "the file") in user input."""

    @abstractmethod
    def get_context_snapshot(self, session_id: str) -> ContextSnapshot | None:
        """Retrieve current prioritized ContextSnapshot."""

    @abstractmethod
    def record_tool_result(
        self, session_id: str, command: dict[str, Any], result: dict[str, Any]
    ) -> None:
        """Record tool execution command and result in context."""

    @property
    @abstractmethod
    def manager_config(self) -> ConversationManagerConfiguration:
        """Active configuration model."""
