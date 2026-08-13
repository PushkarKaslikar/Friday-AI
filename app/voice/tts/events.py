"""EventBus typed events for Text-to-Speech (TTS) Subsystem.

Phase 3.6 - Piper Local Text-to-Speech Engine
"""

import time
from dataclasses import dataclass, field
from typing import Any

from app.services.events.event_models import Event


@dataclass
class TTSSynthesisStarted(Event):
    """Event emitted when speech synthesis begins for a text request."""

    text: str = ""
    voice_name: str = "en_US-amy-medium"
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="TTSSynthesisStarted", init=False)


@dataclass
class TTSSynthesisCompleted(Event):
    """Event published when speech synthesis completes successfully."""

    text: str = ""
    audio_duration_seconds: float = 0.0
    synthesis_time_seconds: float = 0.0
    real_time_factor: float = 0.0
    voice_name: str = "en_US-amy-medium"
    sample_rate: int = 22050
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="TTSSynthesisCompleted", init=False)


@dataclass
class TTSPlaybackStarted(Event):
    """Event emitted when audio output playback starts."""

    text: str = ""
    audio_duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="TTSPlaybackStarted", init=False)


@dataclass
class TTSPlaybackCompleted(Event):
    """Event emitted when audio output playback completes successfully."""

    text: str = ""
    audio_duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="TTSPlaybackCompleted", init=False)


@dataclass
class TTSStopped(Event):
    """Event emitted when TTS speech synthesis or playback is explicitly stopped/cancelled."""

    reason: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="TTSStopped", init=False)


@dataclass
class TTSFailed(Event):
    """Event emitted when TTS synthesis or playback fails."""

    error_message: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="TTSFailed", init=False)


@dataclass
class TTSModelLoaded(Event):
    """Event emitted when Piper voice model finishes loading into memory."""

    voice_name: str = "en_US-amy-medium"
    sample_rate: int = 22050
    load_time_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="TTSModelLoaded", init=False)


@dataclass
class TTSModelUnloaded(Event):
    """Event emitted when Piper voice model unloads from memory."""

    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="TTSModelUnloaded", init=False)


@dataclass
class TTSStateChanged(Event):
    """Event emitted when TTS state transitions."""

    previous_state: str = ""
    new_state: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="TTSStateChanged", init=False)


@dataclass
class TTSError(Event):
    """Event emitted when TTS subsystem encounters an operational error."""

    error_message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="TTSError", init=False)
