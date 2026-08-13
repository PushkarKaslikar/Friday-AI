"""EventBus typed events for Voice Activity Detection (VAD).

Phase 3.4 - Voice Activity Detection & Speech Boundary Engine
"""

import time
from dataclasses import dataclass, field
from typing import Any

from app.services.events.event_models import Event


@dataclass
class SpeechStarted(Event):
    """Event published when confirmed speech activity begins."""

    timestamp: float = field(default_factory=time.time)
    speech_probability: float = 0.0
    threshold: float = 0.50
    audio_timestamp: float = field(default_factory=time.time)
    detector_id: str = "silero_vad"
    event_type: str = field(default="SpeechStarted", init=False)


@dataclass
class SpeechStopped(Event):
    """Event published when speech activity ends after configured silence duration."""

    timestamp: float = field(default_factory=time.time)
    speech_duration: float = 0.0
    final_probability: float = 0.0
    silence_duration: float = 0.0
    audio_start_timestamp: float = 0.0
    audio_end_timestamp: float = 0.0
    detector_id: str = "silero_vad"
    event_type: str = field(default="SpeechStopped", init=False)


@dataclass
class VADDetectorStarted(Event):
    """Event emitted when VADDetector service starts listening."""

    timestamp: float = field(default_factory=time.time)
    model_name: str = "silero_vad"
    sample_rate: int = 16000
    threshold: float = 0.50
    event_type: str = field(default="VADDetectorStarted", init=False)


@dataclass
class VADDetectorStopped(Event):
    """Event emitted when VADDetector service stops listening."""

    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="VADDetectorStopped", init=False)


@dataclass
class VADModelLoaded(Event):
    """Event emitted when Silero VAD model successfully loads into ONNX runtime."""

    timestamp: float = field(default_factory=time.time)
    model_name: str = ""
    model_path: str = ""
    event_type: str = field(default="VADModelLoaded", init=False)


@dataclass
class VADModelUnloaded(Event):
    """Event emitted when Silero VAD model unloads from ONNX runtime."""

    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="VADModelUnloaded", init=False)


@dataclass
class VADStateChanged(Event):
    """Event emitted when VAD state machine transitions state."""

    previous_state: str = ""
    new_state: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="VADStateChanged", init=False)


@dataclass
class VADError(Event):
    """Event emitted when VAD subsystem encounters an error."""

    error_message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="VADError", init=False)
