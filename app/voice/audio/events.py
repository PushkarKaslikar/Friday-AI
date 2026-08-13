"""EventBus model definitions for Audio Engine Subsystem notifications."""

from dataclasses import dataclass

from app.services.events.event_models import Event


@dataclass
class AudioEngineInitialized(Event):
    """Fired when AudioEngine finishes initial setup."""

    sample_rate: int = 16000
    default_input: str = ""
    default_output: str = ""


@dataclass
class AudioEngineReady(Event):
    """Fired when AudioEngine transitions to READY state."""


@dataclass
class AudioInputStarted(Event):
    """Fired when microphone audio capture starts."""

    device_id: str | int = 0
    device_name: str = ""
    sample_rate: int = 16000


@dataclass
class AudioInputStopped(Event):
    """Fired when microphone audio capture stops."""

    reason: str = "User requested stop"


@dataclass
class AudioOutputStarted(Event):
    """Fired when speaker playback stream starts."""

    device_id: str | int = 0
    device_name: str = ""


@dataclass
class AudioOutputStopped(Event):
    """Fired when speaker playback stream stops."""

    reason: str = "Playback stopped"


@dataclass
class AudioDeviceChanged(Event):
    """Fired when input or output device selection changes."""

    device_type: str = "INPUT"
    old_device: str = ""
    new_device: str = ""


@dataclass
class AudioDeviceDisconnected(Event):
    """Fired when a running input/output device is disconnected."""

    device_id: str | int = 0
    device_name: str = ""
    fallback_device: str | None = None


@dataclass
class AudioBufferOverflow(Event):
    """Fired when ring buffer exceeds maximum capacity and drops frames."""

    dropped_frames: int = 1
    total_overflows: int = 1


@dataclass
class AudioError(Event):
    """Fired when a stream or engine error occurs."""

    error_code: str = "AUDIO_ERROR"
    message: str = ""
    details: str = ""


@dataclass
class AudioEngineShutdown(Event):
    """Fired when AudioEngine shuts down resources."""
