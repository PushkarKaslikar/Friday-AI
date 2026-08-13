"""Voice Activity Detection (VAD) Subsystem.

Phase 3.4 - Voice Activity Detection & Speech Boundary Engine
"""

from app.voice.vad.audio_adapter import VADAudioAdapter
from app.voice.vad.diagnostics import VADDiagnostics
from app.voice.vad.events import (
    SpeechStarted,
    SpeechStopped,
    VADDetectorStarted,
    VADDetectorStopped,
    VADError,
    VADModelLoaded,
    VADModelUnloaded,
    VADStateChanged,
)
from app.voice.vad.metrics import VADMetrics
from app.voice.vad.models import SpeechSegment, VADConfiguration, VADState
from app.voice.vad.silero_vad_model import SileroVADModel
from app.voice.vad.state_machine import VADStateMachine
from app.voice.vad.vad_detector import VADDetector
from app.voice.vad.vad_detector_interface import IVADDetector
from app.voice.vad.vad_model_interface import IVADModel

__all__ = [
    "IVADDetector",
    "IVADModel",
    "SileroVADModel",
    "SpeechSegment",
    "SpeechStarted",
    "SpeechStopped",
    "VADAudioAdapter",
    "VADConfiguration",
    "VADDetector",
    "VADDetectorStarted",
    "VADDetectorStopped",
    "VADDiagnostics",
    "VADError",
    "VADMetrics",
    "VADModelLoaded",
    "VADModelUnloaded",
    "VADState",
    "VADStateChanged",
    "VADStateMachine",
]
