"""Wake Word Detection & Voice Activation package for Phase 3.3."""

from app.voice.wakeword.audio_adapter import WakeWordAudioAdapter
from app.voice.wakeword.diagnostics import WakeWordDiagnostics
from app.voice.wakeword.events import (
    WakeWordDetected,
    WakeWordDetectionCooldown,
    WakeWordDetectionError,
    WakeWordDetectorStarted,
    WakeWordDetectorStopped,
    WakeWordModelLoaded,
    WakeWordModelUnloaded,
)
from app.voice.wakeword.metrics import WakeWordMetrics
from app.voice.wakeword.model_provider import WakeWordModelProvider
from app.voice.wakeword.models import (
    WakeWordConfiguration,
    WakeWordEvent,
    WakeWordState,
)
from app.voice.wakeword.wakeword_detector import WakeWordDetector
from app.voice.wakeword.wakeword_detector_interface import IWakeWordDetector

__all__ = [
    "IWakeWordDetector",
    "WakeWordAudioAdapter",
    "WakeWordConfiguration",
    "WakeWordDetected",
    "WakeWordDetectionCooldown",
    "WakeWordDetectionError",
    "WakeWordDetector",
    "WakeWordDetectorStarted",
    "WakeWordDetectorStopped",
    "WakeWordDiagnostics",
    "WakeWordEvent",
    "WakeWordMetrics",
    "WakeWordModelLoaded",
    "WakeWordModelProvider",
    "WakeWordModelUnloaded",
    "WakeWordState",
]
