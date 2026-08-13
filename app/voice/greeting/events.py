"""EventBus typed events for Natural Greetings Foundation.

Phase 3.9 - Natural Greetings Foundation & Context-Aware Activation Responses
"""

import time
from dataclasses import dataclass, field

from app.services.events.event_models import Event


@dataclass
class GreetingGenerationStarted(Event):
    """Event published when greeting generation starts for an activation."""

    session_id: str = ""
    activation_source: str = "WAKE_WORD"
    time_of_day: str = "MORNING"
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="GreetingGenerationStarted", init=False)


@dataclass
class GreetingGenerated(Event):
    """Event published when a greeting response is successfully selected/generated."""

    session_id: str = ""
    text: str = ""
    category: str = "MORNING"
    provider: str = "TemplateGreetingProvider"
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="GreetingGenerated", init=False)


@dataclass
class GreetingSpoken(Event):
    """Event published when TTS playback for a greeting begins/completes."""

    session_id: str = ""
    text: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="GreetingSpoken", init=False)


@dataclass
class GreetingGenerationFailed(Event):
    """Event published when greeting provider encounters an error and fallback is used."""

    session_id: str = ""
    error_message: str = ""
    fallback_used: bool = True
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="GreetingGenerationFailed", init=False)


@dataclass
class GreetingSkipped(Event):
    """Event published when greeting generation is skipped (e.g. disabled in settings)."""

    session_id: str = ""
    reason: str = "greetings_disabled"
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="GreetingSkipped", init=False)
