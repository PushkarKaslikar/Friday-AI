"""Domain models and data structures for Speech-to-Text (STT) Subsystem.

Phase 3.5 - Faster-Whisper Speech-to-Text Engine
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class STTState(str, Enum):
    """STT Engine operational and transcription states."""

    DISABLED = "DISABLED"
    LOADING = "LOADING"
    READY = "READY"
    TRANSCRIBING = "TRANSCRIBING"
    UNLOADING = "UNLOADING"
    UNLOADED = "UNLOADED"
    ERROR = "ERROR"


@dataclass
class TranscriptSegment:
    """Structured segment representation within a transcription result."""

    start: float
    end: float
    text: str
    confidence: float = 1.0


@dataclass
class TranscriptionResult:
    """Structured result object returned by STT engine transcription.

    No raw audio is persisted in this model.
    """

    text: str
    language: str = "en"
    language_probability: float = 1.0
    duration_seconds: float = 0.0
    processing_time_seconds: float = 0.0
    real_time_factor: float = 0.0
    segments: list[TranscriptSegment] = field(default_factory=list)
    model_name: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    timestamp: float = field(default_factory=time.time)
    status: str = "SUCCESS"  # SUCCESS, EMPTY, TOO_SHORT, FAILED
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class STTConfiguration:
    """Configuration settings for Speech-to-Text (STT) Subsystem."""

    enabled: bool = True
    engine: str = "faster_whisper"  # "faster_whisper" or "parakeet"
    model_name: str = "base"
    device: str = "auto"
    compute_type: str = "auto"
    language: str | None = None
    beam_size: int = 5
    max_segment_duration_ms: float = 30000.0
    word_timestamps: bool = False
    vad_filter: bool = False
    custom_model_path: str | None = None
