"""Domain models and data structures for Dynamic Response Generation Engine.

Phase 4.5 - Dynamic Response Generation Engine
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.ai.models.models import ChatMessage
from app.ai.personality.models import PersonalityContext


class ResponseGenerationMode(str, Enum):
    """Structured response generation framing modes."""

    NORMAL = "NORMAL"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    WARNING = "WARNING"
    CLARIFICATION = "CLARIFICATION"
    INFORMATION = "INFORMATION"
    CONFIRMATION = "CONFIRMATION"
    PROGRESS = "PROGRESS"
    CONVERSATIONAL = "CONVERSATIONAL"
    TECHNICAL = "TECHNICAL"
    URGENT = "URGENT"
    CASUAL = "CASUAL"


class ResponseStatus(str, Enum):
    """Factual execution status mapping for response generation."""

    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"
    DENIED = "DENIED"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    FALLBACK_USED = "FALLBACK_USED"


class ResponseTarget(str, Enum):
    """Target rendering channel for generated response."""

    TEXT = "TEXT"
    VOICE = "VOICE"
    BOTH = "BOTH"


@dataclass
class ResponseMetadata:
    """Performance and telemetry metadata for a response generation turn."""

    generation_duration_ms: float = 0.0
    prompt_chars: int = 0
    response_chars: int = 0
    fallback_used: bool = False
    model_name: str = "local-gguf"
    provider_type: str = "llama.cpp"
    sanitized: bool = True
    streaming: bool = False


@dataclass
class ResponseGenerationRequest:
    """Input parameters for a response generation turn."""

    request_id: str
    user_input: str
    messages: list[ChatMessage] = field(default_factory=list)
    reasoning_summary: str | None = None
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    personality_context: PersonalityContext | None = None
    response_mode: ResponseGenerationMode = ResponseGenerationMode.NORMAL
    response_target: ResponseTarget = ResponseTarget.BOTH
    session_id: str | None = None
    turn_id: str | None = None
    max_response_chars: int = 2000
    timestamp: float = field(default_factory=time.time)


@dataclass
class ResponseResult:
    """Final validated and normalized response returned by the generator."""

    request_id: str
    response_text: str
    spoken_text: str
    status: ResponseStatus
    response_mode: ResponseGenerationMode
    metadata: ResponseMetadata
    session_id: str | None = None
    turn_id: str | None = None
    timestamp: float = field(default_factory=time.time)
