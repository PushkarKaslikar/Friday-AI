"""Domain models and data structures for Phase 3.2 Double-Clap Detection & Activation."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.utilities.system_utils import get_timestamp_str


class ClapState(str, Enum):
    """States of the Double-Clap Detection State Machine."""

    IDLE = "IDLE"
    CLAP_DETECTED = "CLAP_DETECTED"
    WAITING_FOR_SECOND_CLAP = "WAITING_FOR_SECOND_CLAP"
    ACTIVATED = "ACTIVATED"
    COOLDOWN = "COOLDOWN"
    ERROR = "ERROR"


class ClapEvent(BaseModel):
    """Representation of a single detected transient audio clap."""

    timestamp: float = Field(description="Monotonic high-precision detection timestamp")
    confidence: float = Field(
        description="Clap detection confidence score (0.0 to 1.0)"
    )
    peak_amplitude: float = Field(description="Peak signal amplitude (0.0 to 1.0)")
    energy: float = Field(description="RMS signal energy")
    duration: float = Field(description="Impulse duration in milliseconds")
    signal_quality: str = Field(
        default="HIGH", description="Quality categorization ('HIGH', 'MEDIUM', 'LOW')"
    )
    timestamp_str: str = Field(
        default_factory=get_timestamp_str, description="ISO timestamp string"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional signal metadata"
    )


class ClapConfiguration(BaseModel):
    """Configuration parameters for clap signal processor and timing state machine."""

    enabled: bool = Field(
        default=True, description="Master enable flag for clap activation"
    )
    min_clap_interval_ms: int = Field(
        default=150, description="Minimum interval between two claps in ms"
    )
    max_clap_interval_ms: int = Field(
        default=1000, description="Maximum interval between two claps in ms"
    )
    cooldown_ms: int = Field(
        default=2000, description="Refractory cooldown period after activation in ms"
    )
    energy_threshold_multiplier: float = Field(
        default=4.5, description="Energy multiplier threshold relative to noise floor"
    )
    min_peak_amplitude: float = Field(
        default=0.15, description="Minimum peak amplitude threshold"
    )
    min_duration_ms: float = Field(
        default=5.0, description="Minimum impulse duration in ms"
    )
    max_duration_ms: float = Field(
        default=60.0, description="Maximum impulse duration in ms"
    )
    confidence_threshold: float = Field(
        default=0.65, description="Minimum confidence for valid clap"
    )
