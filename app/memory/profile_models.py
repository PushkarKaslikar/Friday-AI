"""Domain models and dataclasses for Phase 5.4 User Profile & Personal Context Management.

Phase 5.4 - User Profile & Personal Context Management
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PreferenceState(str, Enum):
    """Status state for structured user preferences."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNKNOWN = "UNKNOWN"


class ProjectStatus(str, Enum):
    """Status lifecycle state for user project profiles."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class WorkflowStatus(str, Enum):
    """Status lifecycle state for user workflow profiles."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"


@dataclass
class UserIdentity:
    """Non-sensitive, explicit user identity information."""

    preferred_name: str = ""
    display_name: str = ""
    profile_created_at: float = field(default_factory=time.time)
    profile_updated_at: float = field(default_factory=time.time)


@dataclass
class ProfilePreferenceItem:
    """Structured user preference entry with source and status tracking."""

    key: str = ""
    value: str = ""
    category: str = "PREFERENCE"
    status: PreferenceState = PreferenceState.ACTIVE
    source: str = "USER_EXPLICIT"
    confidence: float = 1.0
    source_memory_ids: list[str] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)


@dataclass
class UserProjectItem:
    """Persistent user project profile dataclass."""

    project_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    local_path: str = ""
    status: ProjectStatus = ProjectStatus.ACTIVE
    aliases: list[str] = field(default_factory=list)
    related_applications: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    source_memory_ids: list[str] = field(default_factory=list)


@dataclass
class UserContactItem:
    """Explicitly remembered contact profile dataclass."""

    contact_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    aliases: list[str] = field(default_factory=list)
    relationship: str = ""
    organization: str = ""
    notes: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    source_memory_ids: list[str] = field(default_factory=list)


@dataclass
class UserWorkflowItem:
    """Structured recurring workflow profile dataclass."""

    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    steps: list[str] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    source_memory_ids: list[str] = field(default_factory=list)


@dataclass
class UserInteractionPatternItem:
    """Bounded, explainable interaction pattern dataclass."""

    pattern_key: str = ""
    pattern_value: str = ""
    confidence: float = 1.0
    source_memory_ids: list[str] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)


@dataclass
class UserProfile:
    """Root domain UserProfile organizing persistent long-term memories."""

    identity: UserIdentity = field(default_factory=UserIdentity)
    preferences: dict[str, ProfilePreferenceItem] = field(default_factory=dict)
    projects: dict[str, UserProjectItem] = field(default_factory=dict)
    contacts: dict[str, UserContactItem] = field(default_factory=dict)
    workflows: dict[str, UserWorkflowItem] = field(default_factory=dict)
    interaction_patterns: dict[str, UserInteractionPatternItem] = field(
        default_factory=dict
    )
    metadata: dict[str, Any] = field(default_factory=dict)
    last_updated_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class UserProfileSnapshot:
    """Read-only immutable snapshot of user profile for prompt context consumption."""

    preferred_name: str
    preferences_summary: dict[str, str]
    active_projects: list[str]
    known_contacts: list[str]
    active_workflows: list[str]
    interaction_style: str
    formatted_snapshot: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class UserProfileConfig:
    """Configuration settings for Phase 5.4 User Profile."""

    enabled: bool = True
    max_projects: int = 20
    max_contacts: int = 50
    max_workflows: int = 20
    max_snapshot_chars: int = 4000
