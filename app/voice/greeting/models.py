"""Domain models and data structures for Natural Greetings Foundation.

Phase 3.9 - Natural Greetings Foundation & Context-Aware Activation Responses
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TimeOfDay(str, Enum):
    """Classification of local time into daily periods."""

    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    EVENING = "EVENING"
    NIGHT = "NIGHT"


class GreetingCategory(str, Enum):
    """Contextual categories for selecting greeting responses."""

    FIRST_GREETING = "FIRST_GREETING"
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    EVENING = "EVENING"
    NIGHT = "NIGHT"
    RETURNING = "RETURNING"
    CONTINUATION = "CONTINUATION"
    READY = "READY"
    FALLBACK = "FALLBACK"


class GreetingStyle(str, Enum):
    """Assistant greeting style profile."""

    FRIDAY = "FRIDAY"
    PROFESSIONAL = "PROFESSIONAL"
    CONCISE = "CONCISE"
    WARM = "WARM"
    TECHNICAL = "TECHNICAL"


@dataclass
class GreetingContext:
    """Strongly typed contextual data passed to greeting providers."""

    session_id: str = ""
    activation_source: str = "WAKE_WORD"
    time_of_day: TimeOfDay = TimeOfDay.MORNING
    is_new_session: bool = True
    is_returning_session: bool = False
    turn_count: int = 1
    last_user_interaction: str = ""
    last_assistant_interaction: str = ""
    current_conversation_topic: str = "GENERAL"
    user_name: str | None = None
    style: GreetingStyle = GreetingStyle.FRIDAY
    timestamp: float = field(default_factory=time.time)


@dataclass
class GreetingResponse:
    """Structured greeting response model."""

    text: str = "How can I help?"
    category: GreetingCategory = GreetingCategory.FALLBACK
    provider: str = "TemplateGreetingProvider"
    context_version: int = 1
    session_id: str = ""
    should_speak: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GreetingConfiguration:
    """Configuration settings for Natural Greetings Subsystem."""

    enabled: bool = True
    max_recent_history: int = 5
    avoid_repetition: bool = True
    default_style: GreetingStyle = GreetingStyle.FRIDAY
    use_context: bool = True
