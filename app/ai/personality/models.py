"""Domain models and data structures for Personality Engine & Behavioral Identity System.

Phase 4.4 - Personality Engine & Behavioral Identity System
"""

import time
from dataclasses import dataclass, field
from enum import Enum


class EmotionalSignal(str, Enum):
    """Conversational emotional tone signals detected from user input."""

    NEUTRAL = "NEUTRAL"
    POSITIVE = "POSITIVE"
    FRUSTRATED = "FRUSTRATED"
    URGENT = "URGENT"
    CONFUSED = "CONFUSED"
    EXCITED = "EXCITED"


class ResponseStyleMode(str, Enum):
    """Contextual response framing style modes."""

    NORMAL = "NORMAL"
    TECHNICAL = "TECHNICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    SUCCESS = "SUCCESS"
    CLARIFICATION = "CLARIFICATION"
    URGENT = "URGENT"
    CASUAL = "CASUAL"


@dataclass
class IdentityProfile:
    """Core identity configuration for Friday AI Assistant."""

    name: str = "Friday"
    role: str = "Personal AI Assistant"
    description: str = (
        "A highly capable local personal AI assistant designed to help the user manage "
        "tasks, information, applications, files, browser workflows, and conversations."
    )


@dataclass
class CommunicationStyle:
    """Structured communication preferences and numerical scales (0.0 to 1.0)."""

    formality: float = 0.5  # 0.0=Casual, 1.0=Formal
    humor: float = 0.25  # 0.0=None, 1.0=Frequent/Witty
    emotional_responsiveness: float = 0.7  # 0.0=Robot, 1.0=Highly Empathetic
    proactivity: float = 0.4  # 0.0=Reactive, 1.0=Proactive
    conciseness: float = 0.75  # 0.0=Verbose/Detailed, 1.0=Extremely Concise
    tone: str = "calm_professional"


@dataclass
class UserRelationship:
    """User relationship model and address style settings."""

    preferred_name: str | None = None
    address_style: str = "natural"  # "natural", "formal", "casual"
    familiarity: str = "respectful"  # "formal", "respectful", "friendly"
    continuity_preference: bool = True


@dataclass
class BehavioralRule:
    """Immutable behavioral and safety governance rule."""

    rule_id: str
    description: str
    priority: int = 1
    category: str = "BEHAVIOR"


@dataclass
class PersonalityProfile:
    """Central personality profile containing identity, communication, relationship, and rules."""

    identity: IdentityProfile = field(default_factory=IdentityProfile)
    communication: CommunicationStyle = field(default_factory=CommunicationStyle)
    relationship: UserRelationship = field(default_factory=UserRelationship)
    behavioral_rules: list[BehavioralRule] = field(default_factory=list)


@dataclass
class PersonalityModifier:
    """Temporary dynamic personality modifier applied over base profile without mutating base state."""

    source: str
    reason: str
    formality_delta: float = 0.0
    humor_delta: float = 0.0
    emotional_responsiveness_delta: float = 0.0
    proactivity_delta: float = 0.0
    conciseness_delta: float = 0.0
    priority: int = 1
    duration_seconds: float = 300.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class PersonalityContext:
    """Effective personality context generated for LLM model prompt synthesis."""

    identity_name: str
    role: str
    style_mode: ResponseStyleMode
    emotional_signal: EmotionalSignal
    effective_formality: float
    effective_humor: float
    effective_emotional_responsiveness: float
    effective_proactivity: float
    effective_conciseness: float
    system_prompt_snippet: str
    timestamp: float = field(default_factory=time.time)
