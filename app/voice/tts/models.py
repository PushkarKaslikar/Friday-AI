"""Domain models and data structures for Text-to-Speech (TTS) Subsystem.

Phase 3.6 - Piper Local Text-to-Speech Engine
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TTSState(str, Enum):
    """TTS Engine operational and playback states."""

    DISABLED = "DISABLED"
    LOADING = "LOADING"
    READY = "READY"
    SYNTHESIZING = "SYNTHESIZING"
    PLAYING = "PLAYING"
    STOPPING = "STOPPING"
    UNLOADING = "UNLOADING"
    UNLOADED = "UNLOADED"
    ERROR = "ERROR"


@dataclass
class TTSResult:
    """Structured result object returned by TTS engine synthesis.

    No raw audio is persisted in this model long term.
    """

    text: str
    audio_duration_seconds: float = 0.0
    synthesis_time_seconds: float = 0.0
    real_time_factor: float = 0.0
    voice_name: str = "en_US-amy-medium"
    sample_rate: int = 22050
    status: str = "SUCCESS"  # SUCCESS, EMPTY_INPUT, FAILED, CANCELLED
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TTSConfiguration:
    """Configuration settings for Text-to-Speech (TTS) Subsystem."""

    enabled: bool = True
    voice: str = "en_US-amy-medium"
    language: str = "en_US"
    model_path: str | None = None
    config_path: str | None = None
    max_text_length: int = 500
    auto_play: bool = True
    use_cuda: bool = False
    speed_alpha: float = 1.0
    noise_scale: float = 0.667
