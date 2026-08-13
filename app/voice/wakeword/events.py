"""EventBus model definitions for Wake Word Subsystem notifications."""

from dataclasses import dataclass

from app.services.events.event_models import Event


@dataclass
class WakeWordDetected(Event):
    """Core Activation Event: Fired when configured wake word is detected with high confidence."""

    wake_word: str = "friday"
    score: float = 0.0
    threshold: float = 0.70
    timestamp: float = 0.0
    model_id: str = "friday"


@dataclass
class WakeWordDetectorStarted(Event):
    """Fired when WakeWordDetector begins processing audio frames."""

    model_id: str = "friday"


@dataclass
class WakeWordDetectorStopped(Event):
    """Fired when WakeWordDetector stops processing audio frames."""

    reason: str = "Stopped"


@dataclass
class WakeWordDetectionCooldown(Event):
    """Fired when duplicate wake word detections are suppressed during refractory cooldown."""

    wake_word: str = "friday"
    score: float = 0.0


@dataclass
class WakeWordDetectionError(Event):
    """Fired on wake word detector error."""

    error_code: str = "WAKEWORD_DETECTOR_ERROR"
    message: str = ""
    details: str = ""


@dataclass
class WakeWordModelLoaded(Event):
    """Fired when wake word ONNX model is successfully loaded."""

    model_id: str = "friday"
    model_path: str = ""


@dataclass
class WakeWordModelUnloaded(Event):
    """Fired when wake word ONNX model is unloaded."""

    model_id: str = "friday"
