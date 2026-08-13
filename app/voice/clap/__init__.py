"""Double-Clap Detection & Activation package for Phase 3.2."""

from app.voice.clap.clap_detector import ClapDetector
from app.voice.clap.clap_detector_interface import IClapDetector
from app.voice.clap.diagnostics import ClapDiagnostics
from app.voice.clap.events import (
    ClapDetected,
    ClapDetectionError,
    ClapDetectionStarted,
    ClapDetectionStopped,
    DoubleClapDetected,
)
from app.voice.clap.metrics import ClapMetrics
from app.voice.clap.models import ClapConfiguration, ClapEvent, ClapState
from app.voice.clap.signal_processor import ClapSignalProcessor
from app.voice.clap.state_machine import DoubleClapStateMachine

__all__ = [
    "ClapConfiguration",
    "ClapDetected",
    "ClapDetectionError",
    "ClapDetectionStarted",
    "ClapDetectionStopped",
    "ClapDetector",
    "ClapDiagnostics",
    "ClapEvent",
    "ClapMetrics",
    "ClapSignalProcessor",
    "ClapState",
    "DoubleClapDetected",
    "DoubleClapStateMachine",
    "IClapDetector",
]
