"""Deterministic test response provider implementation for Phase 3.7 orchestration testing.

Phase 3.7 - Conversation State Machine & Real-Time Voice Orchestration
"""

from app.voice.conversation.response_provider_interface import (
    IConversationResponseProvider,
)


class TestResponseProvider(IConversationResponseProvider):
    """Deterministic fake response provider for state machine testing."""

    def __init__(
        self, default_response: str = "Hello Pushkar. Friday is online."
    ) -> None:
        self.default_response = default_response

    def get_response(self, transcript: str, session_id: str = "") -> str:
        """Return deterministic test response based on transcript keyword matching."""
        clean = transcript.strip().lower()
        if not clean:
            return self.default_response
        if "hello" in clean or "hi" in clean:
            return "Hello Pushkar. How can I help you today?"
        if "time" in clean:
            return "The current time is 12:30 PM."
        if "status" in clean:
            return "All Friday systems are operational."
        if "stop" in clean or "bye" in clean:
            return "Goodbye Pushkar."

        return f"I heard you say: {transcript}"
