"""EventBus typed events for Dynamic Response Generation Engine.

Phase 4.5 - Dynamic Response Generation Engine
"""

import time
from dataclasses import dataclass, field

from app.services.events.event_models import Event


@dataclass
class ResponseGenerationStarted(Event):
    """Event published when a response generation turn begins."""

    request_id: str = ""
    response_mode: str = "NORMAL"
    user_input: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ResponseGenerationStarted", init=False)


@dataclass
class ResponseGenerationCompleted(Event):
    """Event published when response generation completes successfully."""

    request_id: str = ""
    status: str = "SUCCESS"
    duration_ms: float = 0.0
    response_length: int = 0
    fallback_used: bool = False
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ResponseGenerationCompleted", init=False)


@dataclass
class ResponseGenerationFailed(Event):
    """Event published when response generation fails or uses fallback."""

    request_id: str = ""
    error_message: str = ""
    fallback_used: bool = True
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ResponseGenerationFailed", init=False)
