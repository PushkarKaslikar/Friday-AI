"""Contextual category selector and repetition prevention engine.

Phase 3.9 - Natural Greetings Foundation & Context-Aware Activation Responses
"""

import threading

from app.voice.greeting.models import (
    GreetingCategory,
    GreetingConfiguration,
    GreetingContext,
    TimeOfDay,
)


class GreetingSelector:
    """Determines appropriate greeting category and prevents immediate repetition."""

    def __init__(self, config: GreetingConfiguration | None = None) -> None:
        self.config = config or GreetingConfiguration()
        self._lock = threading.Lock()
        self._recent_greetings: list[str] = []

    def determine_category(self, context: GreetingContext) -> GreetingCategory:
        """Determine target greeting category from context parameters."""
        if not self.config.use_context:
            return GreetingCategory.READY

        if context.is_returning_session or context.turn_count > 1:
            return GreetingCategory.RETURNING

        if context.time_of_day == TimeOfDay.MORNING:
            return GreetingCategory.MORNING
        if context.time_of_day == TimeOfDay.AFTERNOON:
            return GreetingCategory.AFTERNOON
        if context.time_of_day == TimeOfDay.EVENING:
            return GreetingCategory.EVENING
        if context.time_of_day == TimeOfDay.NIGHT:
            return GreetingCategory.NIGHT

        return GreetingCategory.READY

    def filter_candidates(self, candidates: list[str]) -> list[str]:
        """Filter out candidates present in recent history to prevent repetition."""
        with self._lock:
            if not self.config.avoid_repetition or not candidates:
                return candidates

            filtered = [c for c in candidates if c not in self._recent_greetings]
            return filtered if filtered else candidates

    def record_selected_greeting(self, greeting_text: str) -> None:
        """Record selected greeting text in recent history buffer."""
        with self._lock:
            self._recent_greetings.append(greeting_text)
            if len(self._recent_greetings) > self.config.max_recent_history:
                self._recent_greetings.pop(0)

    def clear_history(self) -> None:
        """Clear recent history buffer."""
        with self._lock:
            self._recent_greetings.clear()
