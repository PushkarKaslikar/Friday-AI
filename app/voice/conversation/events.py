"""EventBus typed events for Conversation State Machine & Voice Orchestration.

Phase 3.7 - Conversation State Machine & Real-Time Voice Orchestration
"""

import time
from dataclasses import dataclass, field
from typing import Any

from app.services.events.event_models import Event


@dataclass
class ConversationStateChanged(Event):
    """Event published whenever the conversation state machine changes state."""

    previous_state: str = "IDLE"
    new_state: str = "IDLE"
    session_id: str = ""
    reason: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ConversationStateChanged", init=False)


@dataclass
class ConversationActivated(Event):
    """Event published when a conversation session is activated (clap or wake-word)."""

    session_id: str = ""
    activation_source: str = "WAKE_WORD"
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ConversationActivated", init=False)


@dataclass
class ConversationListeningStarted(Event):
    """Event published when Friday enters LISTENING state waiting for speech."""

    session_id: str = ""
    turn_count: int = 1
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ConversationListeningStarted", init=False)


@dataclass
class ConversationProcessingStarted(Event):
    """Event published when user stops speaking and STT processing begins."""

    session_id: str = ""
    turn_count: int = 1
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ConversationProcessingStarted", init=False)


@dataclass
class ConversationSpeakingStarted(Event):
    """Event published when Friday begins speaking response audio."""

    session_id: str = ""
    text: str = ""
    turn_count: int = 1
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ConversationSpeakingStarted", init=False)


@dataclass
class ConversationSpeakingCompleted(Event):
    """Event published when Friday finishes speaking response audio."""

    session_id: str = ""
    text: str = ""
    turn_count: int = 1
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ConversationSpeakingCompleted", init=False)


@dataclass
class BargeInDetected(Event):
    """Event published when user speech interrupts Friday while speaking."""

    session_id: str = ""
    turn_count: int = 1
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="BargeInDetected", init=False)


@dataclass
class ConversationEnded(Event):
    """Event published when a conversation session ends (timeout or explicit termination)."""

    session_id: str = ""
    reason: str = "session_timeout"
    turn_count: int = 0
    duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ConversationEnded", init=False)


@dataclass
class ConversationError(Event):
    """Event published when conversation orchestration encounters an error."""

    session_id: str = ""
    error_message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ConversationError", init=False)
