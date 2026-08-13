"""Abstract interface contract for response providers in Phase 3.7.

Phase 3.7 - Conversation State Machine & Real-Time Voice Orchestration
"""

from abc import ABC, abstractmethod


class IConversationResponseProvider(ABC):
    """Abstract boundary interface for response generation before Phase 3.8 / LLM integration."""

    @abstractmethod
    def get_response(self, transcript: str, session_id: str = "") -> str:
        """Generate response text for transcribed user input.

        Args:
            transcript: Transcribed user speech text
            session_id: Active conversation session identifier

        Returns:
            str: Response text to be spoken by TTS
        """
