"""Abstract interface contract for Greeting Providers in Phase 3.9.

Phase 3.9 - Natural Greetings Foundation & Context-Aware Activation Responses
"""

from abc import ABC, abstractmethod

from app.voice.greeting.models import GreetingContext, GreetingResponse


class IGreetingProvider(ABC):
    """Abstract boundary interface for context-aware greeting selection and generation."""

    @abstractmethod
    def generate_greeting(self, context: GreetingContext) -> GreetingResponse:
        """Generate greeting response from context.

        Args:
            context: GreetingContext containing session, time of day, and history

        Returns:
            GreetingResponse: Selected greeting response model
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider identifier name."""
