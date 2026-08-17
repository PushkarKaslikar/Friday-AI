"""Domain models and data structures for Phase 5.3 Long-Term Memory & Persistence.

Phase 5.3 - Long-Term Memory & Persistent Memory Foundation
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Categorical classification of long-term stored memory."""

    PREFERENCE = "PREFERENCE"
    PROJECT = "PROJECT"
    FOLDER = "FOLDER"
    APPLICATION = "APPLICATION"
    CONTACT = "CONTACT"
    WORKFLOW = "WORKFLOW"
    FACT = "FACT"
    USER_PREFERENCE = "USER_PREFERENCE"
    COMMUNICATION_PREFERENCE = "COMMUNICATION_PREFERENCE"
    INTERACTION_PATTERN = "INTERACTION_PATTERN"


class MemorySource(str, Enum):
    """Origin source of a long-term memory record."""

    USER_EXPLICIT = "USER_EXPLICIT"
    USER_CONVERSATION = "USER_CONVERSATION"
    TOOL_RESULT = "TOOL_RESULT"
    SYSTEM = "SYSTEM"
    IMPORTED = "IMPORTED"
    DERIVED = "DERIVED"


class MemoryImportance(str, Enum):
    """Relative importance score for persistent memory."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class UserControlState(str, Enum):
    """Lifecycle status of memory record under user control."""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    DELETED = "DELETED"
    ARCHIVED = "ARCHIVED"


class SensitivityLevel(str, Enum):
    """Privacy and security classification level."""

    NORMAL = "NORMAL"
    PERSONAL = "PERSONAL"
    SENSITIVE = "SENSITIVE"
    RESTRICTED = "RESTRICTED"


class MemoryOperation(str, Enum):
    """Supported operation types for structured memory requests."""

    REMEMBER = "REMEMBER"
    FORGET = "FORGET"
    UPDATE = "UPDATE"
    LIST = "LIST"
    GET = "GET"


@dataclass
class LongTermMemoryEntry:
    """Domain model representing a single persistent long-term memory record."""

    memory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    memory_type: MemoryType = MemoryType.PREFERENCE
    subject: str = ""
    content: str = ""
    source: MemorySource = MemorySource.USER_EXPLICIT
    confidence: float = 1.0
    importance: MemoryImportance = MemoryImportance.MEDIUM
    user_control_state: UserControlState = UserControlState.ACTIVE
    sensitivity: SensitivityLevel = SensitivityLevel.NORMAL
    session_origin: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: float | None = None


@dataclass
class MemoryCandidate:
    """Candidate memory extracted from session context eligible for promotion."""

    candidate_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    memory_type: MemoryType = MemoryType.PREFERENCE
    subject: str = ""
    content: str = ""
    source: MemorySource = MemorySource.USER_EXPLICIT
    confidence: float = 1.0
    importance: MemoryImportance = MemoryImportance.MEDIUM
    session_id: str = ""
    explicit_request: bool = True
    sensitivity: SensitivityLevel = SensitivityLevel.NORMAL
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class MemoryRequest(BaseModel):
    """Validated structured memory request model produced by AI / intent engine."""

    operation: MemoryOperation = Field(
        default=MemoryOperation.REMEMBER, description="Requested memory operation"
    )
    memory_type: MemoryType = Field(
        default=MemoryType.PREFERENCE, description="Memory category"
    )
    subject: str = Field(default="", description="Subject identifier or key")
    content: str = Field(default="", description="Value or body text of memory")
    memory_id: str | None = Field(
        default=None, description="Target memory ID for UPDATE or FORGET"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence level (0.0 - 1.0)"
    )
    source: MemorySource = Field(
        default=MemorySource.USER_EXPLICIT, description="Source origin"
    )
    importance: MemoryImportance = Field(
        default=MemoryImportance.MEDIUM, description="Importance level"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata key-value pairs"
    )


@dataclass
class MemoryResult:
    """Structured result returned by LongTermMemoryService operations."""

    status: str = "SUCCESS"
    memory_id: str | None = None
    operation: str = "REMEMBER"
    message: str = ""
    affected_count: int = 1


@dataclass
class LongTermMemoryConfig:
    """Configuration settings for Phase 5.3 Long-Term Persistent Memory."""

    enabled: bool = True
    db_path: str = ""
    max_total_memories: int = 1000
    max_content_chars: int = 1000
    max_metadata_chars: int = 2000
