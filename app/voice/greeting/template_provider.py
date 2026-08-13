"""Deterministic local template greeting provider for Phase 3.9.

Phase 3.9 - Natural Greetings Foundation & Context-Aware Activation Responses
"""

from app.voice.greeting.greeting_provider_interface import IGreetingProvider
from app.voice.greeting.greeting_selector import GreetingSelector
from app.voice.greeting.models import (
    GreetingCategory,
    GreetingContext,
    GreetingResponse,
)

GREETING_TEMPLATES: dict[GreetingCategory, list[str]] = {
    GreetingCategory.MORNING: [
        "Good morning. Ready to get started?",
        "Good morning. What are we working on today?",
        "Good morning. How can I assist you?",
    ],
    GreetingCategory.AFTERNOON: [
        "Good afternoon. What can I take care of?",
        "Good afternoon. Ready when you are.",
        "Good afternoon. How can I assist you?",
    ],
    GreetingCategory.EVENING: [
        "Good evening. What would you like me to handle?",
        "Good evening. Shall we continue?",
        "Good evening. How can I assist you?",
    ],
    GreetingCategory.NIGHT: [
        "Late night session. How can I help?",
        "Good evening. Ready when you are.",
        "Online and ready.",
    ],
    GreetingCategory.RETURNING: [
        "Welcome back. Shall we continue where we left off?",
        "You're back. Ready to continue?",
        "Welcome back. How can I assist?",
    ],
    GreetingCategory.READY: [
        "Friday is online. How can I help?",
        "Ready when you are.",
        "Online and ready.",
    ],
    GreetingCategory.FALLBACK: [
        "How can I help?",
    ],
}


class TemplateGreetingProvider(IGreetingProvider):
    """Deterministic local template provider selecting context-aware greetings."""

    def __init__(self, selector: GreetingSelector | None = None) -> None:
        self.selector = selector or GreetingSelector()

    @property
    def provider_name(self) -> str:
        """Return provider identifier."""
        return "TemplateGreetingProvider"

    def generate_greeting(self, context: GreetingContext) -> GreetingResponse:
        """Select context-aware greeting template."""
        category = self.selector.determine_category(context)
        pool = (
            GREETING_TEMPLATES.get(category)
            or GREETING_TEMPLATES[GreetingCategory.FALLBACK]
        )

        # Filter out recent greetings to prevent repetition
        candidates = self.selector.filter_candidates(pool)

        # Deterministic index selection based on session_id hash or turn count
        idx = abs(hash(context.session_id + str(context.turn_count))) % len(candidates)
        selected_text = candidates[idx]

        # Personalize if user_name is present
        if (
            context.user_name
            and "Pushkar" not in selected_text
            and "good morning" in selected_text.lower()
        ):
            selected_text = selected_text.replace(
                "Good morning.", f"Good morning {context.user_name}."
            )

        self.selector.record_selected_greeting(selected_text)

        return GreetingResponse(
            text=selected_text,
            category=category,
            provider=self.provider_name,
            session_id=context.session_id,
            should_speak=True,
        )
