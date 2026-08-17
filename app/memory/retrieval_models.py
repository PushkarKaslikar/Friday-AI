"""Domain models, enums, requests, results, and configuration for Memory Retrieval Subsystem.

Phase 5.6 - Memory Retrieval & Relevant Context Engine
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RetrievalStatus(str, Enum):
    """Operational status of a memory retrieval attempt."""

    NO_RETRIEVAL_REQUIRED = "NO_RETRIEVAL_REQUIRED"
    SEARCHED = "SEARCHED"
    MEMORIES_FOUND = "MEMORIES_FOUND"
    NO_RELEVANT_MEMORIES = "NO_RELEVANT_MEMORIES"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"


class RetrievalMode(str, Enum):
    """Modes governing memory retrieval execution."""

    AUTO = "AUTO"
    NONE = "NONE"
    EXPLICIT = "EXPLICIT"
    SESSION_FIRST = "SESSION_FIRST"
    PROFILE_FIRST = "PROFILE_FIRST"
    SEMANTIC = "SEMANTIC"


@dataclass
class MemoryRetrievalRequest:
    """Input payload requesting memory retrieval for a user turn."""

    request_id: str
    user_text: str
    session_id: str | None = None
    current_intent: str | None = None
    current_action: str | None = None
    current_entities: list[str] = field(default_factory=list)
    current_topic: str | None = None
    current_task: str | None = None
    max_results: int = 5
    relevance_threshold: float = 0.35
    include_profile: bool = True
    include_preferences: bool = True
    include_projects: bool = True
    include_workflows: bool = True
    include_contacts: bool = True
    allow_semantic_search: bool = True
    allow_structured_search: bool = True
    mode: RetrievalMode = RetrievalMode.AUTO
    timestamp: float = field(default_factory=time.time)


@dataclass
class CandidateMemory:
    """A scored candidate memory record under consideration for selection."""

    memory_id: str
    memory_type: str
    subject: str
    content: str
    source: str
    confidence: float
    importance: str
    created_at: float
    updated_at: float
    expires_at: float | None = None
    user_control_state: str = "ACTIVE"
    metadata: dict[str, Any] = field(default_factory=dict)

    # Scored ranking components
    semantic_similarity: float = 0.0
    recency_score: float = 0.0
    importance_score: float = 0.0
    confidence_score: float = 0.0
    source_score: float = 0.0
    context_match_score: float = 0.0
    final_score: float = 0.0
    selection_reason: str = ""


@dataclass
class MemoryRetrievalResult:
    """Output summary returned by MemoryRetrievalService."""

    request_id: str
    selected_memories: list[CandidateMemory] = field(default_factory=list)
    total_candidates: int = 0
    filtered_candidates: int = 0
    selected_count: int = 0
    retrieval_status: RetrievalStatus = RetrievalStatus.NO_RETRIEVAL_REQUIRED
    latency_ms: float = 0.0
    context_text: str = ""
    context_characters: int = 0
    degraded_mode: bool = False
    mode_used: RetrievalMode = RetrievalMode.AUTO
    source_info: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class MemoryRetrievalConfig:
    """Configuration settings bounding Memory Retrieval Subsystem behavior."""

    enabled: bool = True
    auto_trigger: bool = True
    max_candidates: int = 15
    max_results: int = 5
    similarity_threshold: float = 0.35
    max_context_characters: int = 1500
    max_context_memories: int = 5
    semantic_weight: float = 0.40
    recency_weight: float = 0.15
    importance_weight: float = 0.15
    confidence_weight: float = 0.15
    source_weight: float = 0.15
    context_match_weight: float = 0.10
    session_priority: bool = True
    profile_priority: bool = True
    retrieval_timeout_s: float = 1.5
