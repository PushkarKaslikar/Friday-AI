"""Domain models and data structures for Phase 5.1 Short-Term Memory Subsystem.

Phase 5.1 - Short-Term Memory Foundation & Active Conversation Memory
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MemoryEntryType(str, Enum):
    """Categorization of short-term memory entries."""

    USER_MESSAGE = "USER_MESSAGE"
    ASSISTANT_MESSAGE = "ASSISTANT_MESSAGE"
    INTENT = "INTENT"
    ENTITY = "ENTITY"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    TASK = "TASK"
    CLARIFICATION = "CLARIFICATION"
    CORRECTION = "CORRECTION"
    REFERENCE = "REFERENCE"
    SYSTEM_CONTEXT = "SYSTEM_CONTEXT"


class MemorySource(str, Enum):
    """Origin source of short-term memory information."""

    USER = "USER"
    ASSISTANT = "ASSISTANT"
    TOOL = "TOOL"
    SYSTEM = "SYSTEM"
    APPLICATION = "APPLICATION"


class MemoryImportance(str, Enum):
    """Priority level for memory retention and eviction."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class MemoryEntry:
    """A single bounded, strongly-typed short-term memory item."""

    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    turn_id: str = ""
    turn_number: int = 1
    timestamp: float = field(default_factory=time.time)
    type: MemoryEntryType = MemoryEntryType.USER_MESSAGE
    source: MemorySource = MemorySource.USER
    importance: MemoryImportance = MemoryImportance.MEDIUM
    content: Any = ""
    entity_metadata: dict[str, Any] = field(default_factory=dict)
    expiration: float | None = None
    confidence: float = 1.0
    is_valid: bool = True
    version: int = 1


@dataclass
class ShortTermMemorySnapshot:
    """Read-only, immutable snapshot of active short-term conversational context."""

    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    version: int = 1
    created_at: float = field(default_factory=time.time)
    recent_turns: list[dict[str, Any]] = field(default_factory=list)
    active_entities: list[dict[str, Any]] = field(default_factory=list)
    current_task: dict[str, Any] | None = None
    pending_clarification: dict[str, Any] | None = None
    recent_actions: list[dict[str, Any]] = field(default_factory=list)
    recent_tool_results: list[dict[str, Any]] = field(default_factory=list)
    current_topic: str = "GENERAL"
    conversational_state: str = "NEW_REQUEST"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ShortTermMemoryConfig:
    """Configuration options for bounded short-term memory execution."""

    enabled: bool = True
    max_entries: int = 100
    max_turns: int = 20
    max_entities: int = 30
    max_context_characters: int = 4000
    max_tool_result_characters: int = 2000
    max_entry_size: int = 1000
    eviction_policy: str = "RECENCY_PRIORITY"
