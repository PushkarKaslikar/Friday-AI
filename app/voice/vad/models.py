"""Domain models and data structures for Voice Activity Detection (VAD).

Phase 3.4 - Voice Activity Detection & Speech Boundary Engine
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class VADState(str, Enum):
    """VAD Detector operational and speech tracking states."""

    DISABLED = "DISABLED"
    LOADING = "LOADING"
    READY = "READY"
    IDLE = "IDLE"
    SPEECH_CANDIDATE = "SPEECH_CANDIDATE"
    SPEAKING = "SPEAKING"
    SILENCE_CANDIDATE = "SILENCE_CANDIDATE"
    ERROR = "ERROR"


@dataclass
class SpeechSegment:
    """Structured tracking model representing a single active speech segment.

    No raw audio is persisted in this model.
    """

    start_timestamp: float
    end_timestamp: float = 0.0
    duration_seconds: float = 0.0
    peak_probability: float = 0.0
    average_probability: float = 0.0
    frame_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def update_frame(self, probability: float) -> None:
        """Update probability statistics for a processed speech frame."""
        self.frame_count += 1
        self.peak_probability = max(self.peak_probability, probability)
        # Rolling average update
        self.average_probability += (
            probability - self.average_probability
        ) / self.frame_count

    def finalize(self, end_time: float) -> None:
        """Finalize segment timing upon speech end detection."""
        self.end_timestamp = end_time
        self.duration_seconds = max(0.0, self.end_timestamp - self.start_timestamp)


@dataclass
class VADConfiguration:
    """Configuration settings for Voice Activity Detection."""

    enabled: bool = True
    model_name: str = "silero_vad"
    custom_model_path: str = ""
    speech_threshold: float = 0.50
    negative_threshold: float = 0.35
    speech_start_confirmation_ms: float = 64.0
    min_silence_duration_ms: float = 300.0
    speech_pad_ms: float = 64.0
    sample_rate: int = 16000
    frame_duration_ms: float = 32.0
