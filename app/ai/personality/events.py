"""EventBus typed events for Personality Engine & Behavioral Identity System.

Phase 4.4 - Personality Engine & Behavioral Identity System
"""

import time
from dataclasses import dataclass, field

from app.services.events.event_models import Event


@dataclass
class PersonalityContextGenerated(Event):
    """Event published when a model-facing personality context is generated."""

    identity_name: str = "Friday"
    style_mode: str = "NORMAL"
    emotional_signal: str = "NEUTRAL"
    prompt_snippet_length: int = 0
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="PersonalityContextGenerated", init=False)


@dataclass
class PersonalityModifierApplied(Event):
    """Event published when a temporary dynamic context modifier is applied."""

    source: str = ""
    reason: str = ""
    style_mode: str = "NORMAL"
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="PersonalityModifierApplied", init=False)


@dataclass
class PersonalityProfileUpdated(Event):
    """Event published when base personality profile configuration changes."""

    name: str = "Friday"
    formality: float = 0.5
    humor: float = 0.25
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="PersonalityProfileUpdated", init=False)
