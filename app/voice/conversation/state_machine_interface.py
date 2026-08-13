"""Abstract interface contract for Conversation State Machine.

Phase 3.7 - Conversation State Machine & Real-Time Voice Orchestration
"""

from abc import ABC, abstractmethod

from app.voice.conversation.models import (
    ActivationSource,
    ConversationConfiguration,
    ConversationSession,
    ConversationState,
)


class IConversationStateMachine(ABC):
    """Abstract interface contract for real-time conversation state machine."""

    @abstractmethod
    def activate(
        self, source: ActivationSource = ActivationSource.WAKE_WORD
    ) -> ConversationSession:
        """Activate conversation session from Double-Clap or Wake-Word trigger.

        Args:
            source: Trigger source (DOUBLE_CLAP or WAKE_WORD)

        Returns:
            ConversationSession: Activated session context.
        """

    @abstractmethod
    def provide_response(self, text: str) -> None:
        """Provide response text to be spoken by TTS in current active session."""

    @abstractmethod
    def stop_speaking(self) -> None:
        """Stop current TTS playback and trigger barge-in transition."""

    @abstractmethod
    def end_conversation(self, reason: str = "user_requested") -> None:
        """Explicitly end the active conversation session and return to IDLE."""

    @property
    @abstractmethod
    def state(self) -> ConversationState:
        """Current public conversation state."""

    @property
    @abstractmethod
    def active_session(self) -> ConversationSession | None:
        """Current active conversation session metadata."""

    @property
    @abstractmethod
    def conversation_config(self) -> ConversationConfiguration:
        """Active conversation state machine configuration."""

    @property
    @abstractmethod
    def is_active(self) -> bool:
        """Check if conversation session is currently active (not IDLE)."""
