"""Domain models and data structures for Conversation State Machine & Voice Orchestration.

Phase 3.7 - Conversation State Machine & Real-Time Voice Orchestration
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConversationState(str, Enum):
    """Core public states of the real-time conversation state machine."""

    IDLE = "IDLE"
    AWAKENING = "AWAKENING"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"
    CONVERSATION_ACTIVE = "CONVERSATION_ACTIVE"


class ActivationSource(str, Enum):
    """Source trigger of conversation activation."""

    DOUBLE_CLAP = "DOUBLE_CLAP"
    WAKE_WORD = "WAKE_WORD"
    MANUAL = "MANUAL"


@dataclass
class StateTransition:
    """Record of a single state machine transition event."""

    previous_state: ConversationState
    new_state: ConversationState
    event_name: str
    session_id: str
    timestamp: float = field(default_factory=time.time)
    reason: str = ""


@dataclass
class ConversationSession:
    """Session context tracking active multi-turn conversation metadata."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    activation_source: ActivationSource = ActivationSource.WAKE_WORD
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    current_state: ConversationState = ConversationState.IDLE
    turn_count: int = 0
    active_tts_request_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationConfiguration:
    """Configuration settings for Conversation State Machine Subsystem."""

    enabled: bool = True
    session_timeout_seconds: float = 10.0
    barge_in_enabled: bool = True
    minimum_barge_in_duration_ms: float = 100.0
    max_turns: int = 50
