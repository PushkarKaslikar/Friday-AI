"""EventBus typed events for Conversation Manager & Short-Term Memory.

Phase 3.8 - Conversation Manager, Session Context & Short-Term Memory
"""

import time
from dataclasses import dataclass, field

from app.services.events.event_models import Event


@dataclass
class ConversationSessionStarted(Event):
    """Event published when a Conversation Manager session context is initialized."""

    session_id: str = ""
    activation_source: str = "WAKE_WORD"
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ConversationSessionStarted", init=False)


@dataclass
class ConversationSessionEnded(Event):
    """Event published when a Conversation Manager session finishes and memory is flushed."""

    session_id: str = ""
    reason: str = "normal_completion"
    turn_count: int = 0
    duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ConversationSessionEnded", init=False)


@dataclass
class ConversationTurnStarted(Event):
    """Event published when a new conversational turn begins."""

    session_id: str = ""
    turn_number: int = 1
    speaker: str = "USER"
    text: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ConversationTurnStarted", init=False)


@dataclass
class ConversationTurnCompleted(Event):
    """Event published when a conversational turn completes with response."""

    session_id: str = ""
    turn_number: int = 1
    user_text: str = ""
    assistant_text: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ConversationTurnCompleted", init=False)


@dataclass
class ContextUpdated(Event):
    """Event published when context snapshot is re-built and updated."""

    session_id: str = ""
    turn_number: int = 1
    context_version: int = 1
    entity_count: int = 0
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ContextUpdated", init=False)


@dataclass
class ContextEvicted(Event):
    """Event published when old turns or entities are evicted due to context bounds."""

    session_id: str = ""
    evicted_turns_count: int = 0
    reason: str = "max_turns_exceeded"
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ContextEvicted", init=False)


@dataclass
class ReferenceResolved(Event):
    """Event published when a pronoun/reference ("it", "the file") is successfully resolved."""

    session_id: str = ""
    reference_text: str = ""
    resolved_entity_name: str = ""
    entity_category: str = "GENERAL"
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ReferenceResolved", init=False)


@dataclass
class ReferenceAmbiguous(Event):
    """Event published when a reference matches multiple candidate entities with equal recency."""

    session_id: str = ""
    reference_text: str = ""
    candidate_names: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ReferenceAmbiguous", init=False)


@dataclass
class ClarificationRequired(Event):
    """Event published when missing required information triggers a clarification prompt."""

    session_id: str = ""
    pending_id: str = ""
    clarification_prompt: str = ""
    missing_fields: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ClarificationRequired", init=False)


@dataclass
class ClarificationResolved(Event):
    """Event published when user clarification response fills a pending request."""

    session_id: str = ""
    pending_id: str = ""
    resolved_param: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ClarificationResolved", init=False)
