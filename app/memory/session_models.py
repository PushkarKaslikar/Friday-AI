"""Domain models and data structures for Phase 5.2 Session Memory & Active Session Context.

Phase 5.2 - Session Memory & Active Session Context Management
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskState(str, Enum):
    """Execution status of an active session task."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class SessionTask:
    """Record of a task executing within the active session context."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_name: str = ""
    state: TaskState = TaskState.ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionWorkflow:
    """Record of an active or completed workflow sequence in session context."""

    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    current_step: int = 1
    total_steps: int = 1
    status: str = "COMPLETED"
    entities: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class SessionContext:
    """In-memory state container holding active session-level context."""

    session_id: str = ""
    status: str = "ACTIVE"
    current_task: SessionTask | None = None
    current_topic: str = "GENERAL"
    recent_topics: list[str] = field(default_factory=lambda: ["GENERAL"])
    active_entities: list[dict[str, Any]] = field(default_factory=list)
    entity_relationships: dict[str, list[str]] = field(default_factory=dict)
    pending_request: dict[str, Any] | None = None
    recent_workflows: list[SessionWorkflow] = field(default_factory=list)
    session_preferences: dict[str, Any] = field(default_factory=dict)
    version: int = 1
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)


@dataclass
class SessionMemorySnapshot:
    """Read-only, immutable snapshot of active session context."""

    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    version: int = 1
    status: str = "ACTIVE"
    created_at: float = field(default_factory=time.time)
    current_task: dict[str, Any] | None = None
    current_topic: str = "GENERAL"
    recent_topics: list[str] = field(default_factory=list)
    active_entities: list[dict[str, Any]] = field(default_factory=list)
    entity_relationships: dict[str, list[str]] = field(default_factory=dict)
    pending_request: dict[str, Any] | None = None
    recent_workflows: list[dict[str, Any]] = field(default_factory=list)
    session_preferences: dict[str, Any] = field(default_factory=dict)
    turn_count: int = 0
    last_activity: float = field(default_factory=time.time)


@dataclass
class SessionMemoryConfig:
    """Configuration options for bounded Session Memory execution."""

    enabled: bool = True
    max_tasks: int = 10
    max_topics: int = 10
    max_workflows: int = 10
    max_entities: int = 30
    max_snapshot_characters: int = 4000
    max_session_preferences: int = 20
