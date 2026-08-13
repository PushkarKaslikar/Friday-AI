"""Greeting Context Builder & Time-of-Day classification engine.

Phase 3.9 - Natural Greetings Foundation & Context-Aware Activation Responses
"""

from datetime import datetime

from app.voice.conversation.conversation_manager import ConversationManager
from app.voice.greeting.models import GreetingContext, TimeOfDay


class GreetingContextBuilder:
    """Builds strongly typed GreetingContext querying ConversationManager and local clock."""

    def __init__(self, conversation_manager: ConversationManager | None = None) -> None:
        self.conversation_manager = conversation_manager

    def build_context(
        self,
        session_id: str,
        activation_source: str = "WAKE_WORD",
    ) -> GreetingContext:
        """Construct GreetingContext model for session activation."""
        time_of_day = self.get_time_of_day()

        is_new = True
        is_returning = False
        turns = 1
        last_user = ""
        last_assistant = ""
        topic = "GENERAL"

        if self.conversation_manager and session_id:
            snapshot = self.conversation_manager.get_context_snapshot(session_id)
            if snapshot:
                turns = len(snapshot.recent_turns) + 1
                is_new = turns <= 1
                is_returning = turns > 1
                last_user = snapshot.last_user_request
                last_assistant = snapshot.last_assistant_response
                topic = snapshot.current_topic

        return GreetingContext(
            session_id=session_id,
            activation_source=activation_source,
            time_of_day=time_of_day,
            is_new_session=is_new,
            is_returning_session=is_returning,
            turn_count=turns,
            last_user_interaction=last_user,
            last_assistant_interaction=last_assistant,
            current_conversation_topic=topic,
        )

    @staticmethod
    def get_time_of_day(now_hour: int | None = None) -> TimeOfDay:
        """Classify current hour into daily TimeOfDay period."""
        if now_hour is None:
            now_hour = datetime.now().astimezone().hour

        if 5 <= now_hour < 12:
            return TimeOfDay.MORNING
        if 12 <= now_hour < 17:
            return TimeOfDay.AFTERNOON
        if 17 <= now_hour < 22:
            return TimeOfDay.EVENING

        return TimeOfDay.NIGHT
