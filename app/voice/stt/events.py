"""EventBus typed events for Speech-to-Text (STT) Subsystem.

Phase 3.5 - Faster-Whisper Speech-to-Text Engine
"""

import time
from dataclasses import dataclass, field
from typing import Any

from app.services.events.event_models import Event


@dataclass
class TranscriptionStarted(Event):
    """Event emitted when speech segment transcription begins."""

    audio_duration_seconds: float = 0.0
    model_name: str = "base"
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="TranscriptionStarted", init=False)


@dataclass
class TranscriptionCompleted(Event):
    """Event published when speech segment transcription completes successfully."""

    text: str = ""
    language: str = "en"
    language_probability: float = 1.0
    audio_duration_seconds: float = 0.0
    processing_time_seconds: float = 0.0
    real_time_factor: float = 0.0
    model_name: str = "base"
    device: str = "cpu"
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="TranscriptionCompleted", init=False)


@dataclass
class TranscriptionFailed(Event):
    """Event emitted when speech segment transcription fails."""

    error_message: str = ""
    audio_duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="TranscriptionFailed", init=False)


@dataclass
class TranscriptionCancelled(Event):
    """Event emitted when a transcription job is cancelled."""

    reason: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="TranscriptionCancelled", init=False)


@dataclass
class STTModelLoaded(Event):
    """Event emitted when Faster-Whisper model finishes loading into memory/GPU."""

    model_name: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    load_time_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="STTModelLoaded", init=False)


@dataclass
class STTModelUnloaded(Event):
    """Event emitted when Faster-Whisper model unloads from memory."""

    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="STTModelUnloaded", init=False)


@dataclass
class STTStateChanged(Event):
    """Event emitted when STT state transitions."""

    previous_state: str = ""
    new_state: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="STTStateChanged", init=False)


@dataclass
class STTError(Event):
    """Event emitted when STT subsystem encounters an error."""

    error_message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="STTError", init=False)
