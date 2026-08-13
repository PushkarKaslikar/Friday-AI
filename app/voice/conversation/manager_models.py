"""Domain models and data structures for Conversation Manager & Short-Term Memory.

Phase 3.8 & Phase 4.7 - Conversational Continuity & Short-Term Memory
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SessionStatus(str, Enum):
    """Lifecycle status of a conversation session context."""

    ACTIVE = "ACTIVE"
    ENDING = "ENDING"
    ENDED = "ENDED"
    TIMED_OUT = "TIMED_OUT"
    ERROR = "ERROR"


class SpeakerRole(str, Enum):
    """Speaker role identifier for conversation turns."""

    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"


class EntityCategory(str, Enum):
    """Classification categories for tracked conversation entities."""

    APPLICATION = "APPLICATION"
    FILE = "FILE"
    FOLDER = "FOLDER"
    WEBSITE = "WEBSITE"
    PROCESS = "PROCESS"
    WINDOW = "WINDOW"
    TOPIC = "TOPIC"
    GENERAL = "GENERAL"


class ReferenceResolutionStatus(str, Enum):
    """Resolution status outcome for conversational entity reference lookup."""

    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_FOUND = "NOT_FOUND"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ConversationalStateCategory(str, Enum):
    """Classification categories for conversational turn relationships in Phase 4.7."""

    NEW_REQUEST = "NEW_REQUEST"
    CONTINUATION = "CONTINUATION"
    CLARIFICATION_RESPONSE = "CLARIFICATION_RESPONSE"
    FOLLOW_UP = "FOLLOW_UP"
    CORRECTION = "CORRECTION"
    RETRY = "RETRY"
    NEW_TOPIC = "NEW_TOPIC"
    COMPLETION_FOLLOW_UP = "COMPLETION_FOLLOW_UP"


@dataclass
class ConversationTurn:
    """Record of a single conversational turn (user or assistant)."""

    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    turn_number: int = 1
    timestamp: float = field(default_factory=time.time)
    speaker: SpeakerRole = SpeakerRole.USER
    text: str = ""
    status: str = "COMPLETED"
    conversational_state: ConversationalStateCategory = (
        ConversationalStateCategory.NEW_REQUEST
    )
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrackedEntity:
    """Structure representing a tracked entity in short-term memory."""

    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: EntityCategory = EntityCategory.GENERAL
    name: str = ""
    identifier: str = ""
    source: str = "USER_INPUT"
    turn_number: int = 1
    confidence: float = 1.0
    last_seen: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReferenceResolutionResult:
    """Result container for reference resolution lookup."""

    status: ReferenceResolutionStatus = ReferenceResolutionStatus.NOT_FOUND
    reference_text: str = ""
    resolved_entity: TrackedEntity | None = None
    candidates: list[TrackedEntity] = field(default_factory=list)
    confidence: float = 0.0
    reason: str = ""


@dataclass
class PendingRequest:
    """Represents a pending user request awaiting missing clarification parameter."""

    pending_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    turn_number: int = 1
    original_text: str = ""
    original_intent: str = ""
    missing_fields: list[str] = field(default_factory=list)
    clarification_prompt: str = ""
    expected_entity_type: str = "GENERAL"
    candidate_options: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 60.0)


@dataclass
class ContextSnapshot:
    """Immutable, prioritized snapshot of conversational context for AI / Intent Engine."""

    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    version: int = 1
    created_at: float = field(default_factory=time.time)
    recent_turns: list[dict[str, Any]] = field(default_factory=list)
    active_entities: list[dict[str, Any]] = field(default_factory=list)
    recent_commands: list[dict[str, Any]] = field(default_factory=list)
    recent_results: list[dict[str, Any]] = field(default_factory=list)
    current_topic: str = "GENERAL"
    last_user_request: str = ""
    last_assistant_response: str = ""
    pending_request: dict[str, Any] | None = None
    conversational_state: ConversationalStateCategory = (
        ConversationalStateCategory.NEW_REQUEST
    )


@dataclass
class ConversationManagerConfiguration:
    """Configuration settings for Conversation Manager Subsystem."""

    enabled: bool = True
    max_turns: int = 20
    max_context_characters: int = 4000
    max_context_tokens: int = 1000
    max_entities: int = 30
    max_tool_result_chars: int = 2000
    pending_request_timeout_seconds: float = 60.0
    context_compaction_enabled: bool = True
