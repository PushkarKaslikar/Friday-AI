"""EventBus model definitions for Double-Clap Subsystem notifications."""

from dataclasses import dataclass

from app.services.events.event_models import Event


@dataclass
class ClapDetected(Event):
    """Fired when a valid single clap transient is recognized."""

    timestamp: float = 0.0
    confidence: float = 0.0
    peak_amplitude: float = 0.0
    energy: float = 0.0


@dataclass
class DoubleClapDetected(Event):
    """Core Activation Event: Fired when two valid claps occur within the configured timing window."""

    first_clap_timestamp: float = 0.0
    second_clap_timestamp: float = 0.0
    interval_ms: float = 0.0
    confidence: float = 0.0


@dataclass
class ClapDetectionStarted(Event):
    """Fired when ClapDetector begins consuming frames."""


@dataclass
class ClapDetectionStopped(Event):
    """Fired when ClapDetector stops consuming frames."""

    reason: str = "Stopped"


@dataclass
class ClapDetectionError(Event):
    """Fired on clap detector error."""

    error_code: str = "CLAP_DETECTOR_ERROR"
    message: str = ""
    details: str = ""
