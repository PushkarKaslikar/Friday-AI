"""Abstract boundary contract for Personality Engine & Behavioral Identity System.

Phase 4.4 - Personality Engine & Behavioral Identity System
"""

from abc import ABC, abstractmethod

from app.ai.personality.models import (
    PersonalityContext,
    PersonalityModifier,
    PersonalityProfile,
    ResponseStyleMode,
)


class IPersonalityEngine(ABC):
    """Abstract interface contract for Personality Engine."""

    @abstractmethod
    def get_personality_profile(self) -> PersonalityProfile:
        """Retrieve active base personality profile."""

    @abstractmethod
    def generate_personality_context(
        self,
        user_input: str = "",
        style_mode: ResponseStyleMode = ResponseStyleMode.NORMAL,
        modifiers: list[PersonalityModifier] | None = None,
    ) -> PersonalityContext:
        """Generate effective model-facing PersonalityContext for a request."""

    @abstractmethod
    def build_model_system_prompt_snippet(self, context: PersonalityContext) -> str:
        """Format compact system prompt snippet for LLM inference instructions."""

    @abstractmethod
    def apply_temporary_modifier(self, modifier: PersonalityModifier) -> None:
        """Stack temporary personality modifier onto active context."""

    @abstractmethod
    def clear_modifiers(self) -> None:
        """Clear all active temporary modifiers."""
