"""Domain models and data structures for Phase 3.3 Wake Word Detection & Voice Activation."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.utilities.system_utils import get_timestamp_str


class WakeWordState(str, Enum):
    """States of the Wake Word Detector Subsystem."""

    DISABLED = "DISABLED"
    LOADING = "LOADING"
    READY = "READY"
    LISTENING = "LISTENING"
    DETECTED = "DETECTED"
    COOLDOWN = "COOLDOWN"
    ERROR = "ERROR"


class WakeWordEvent(BaseModel):
    """Representation of a detected wake word event."""

    timestamp: float = Field(description="Monotonic high-precision detection timestamp")
    wake_word: str = Field(
        description="Detected wake word name (e.g. 'friday', 'hey_jarvis')"
    )
    score: float = Field(description="OpenWakeWord model inference score (0.0 to 1.0)")
    threshold: float = Field(description="Configured confidence score threshold")
    model_id: str = Field(description="Identifier or path of active wake word model")
    signal_quality: str = Field(
        default="HIGH", description="Quality categorization ('HIGH', 'MEDIUM', 'LOW')"
    )
    timestamp_str: str = Field(
        default_factory=get_timestamp_str, description="ISO timestamp string"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional inference metadata"
    )


class WakeWordConfiguration(BaseModel):
    """Configuration parameters for WakeWordDetector service and model provider."""

    enabled: bool = Field(
        default=True, description="Master enable flag for wake word activation"
    )
    model_name: str = Field(
        default="friday", description="Configured target wake word model identifier"
    )
    custom_model_path: str | None = Field(
        default=None, description="Optional custom .onnx model path"
    )
    threshold: float = Field(
        default=0.70, description="Minimum confidence score threshold"
    )
    cooldown_ms: int = Field(
        default=2000, description="Refractory cooldown period after detection in ms"
    )
    sample_rate: int = Field(
        default=16000, description="Expected audio sample rate in Hz"
    )
    audio_adapter_enabled: bool = Field(
        default=True,
        description="Enable automatic float32 to int16 PCM format conversion",
    )
