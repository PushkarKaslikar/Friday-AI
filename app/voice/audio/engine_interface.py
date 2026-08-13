"""Abstract interface contract for Audio Engine Subsystem implementations."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from app.voice.audio.models import (
    AudioConfiguration,
    AudioDevice,
    AudioEngineState,
    AudioFrame,
    AudioStreamState,
)


class IAudioEngine(ABC):
    """Abstract contract enforcing Audio Engine methods decoupled from sounddevice implementation."""

    @property
    @abstractmethod
    def state(self) -> AudioEngineState:
        """Get current AudioEngine lifecycle state."""

    @property
    @abstractmethod
    def input_state(self) -> AudioStreamState:
        """Get current input stream state."""

    @property
    @abstractmethod
    def output_state(self) -> AudioStreamState:
        """Get current output stream state."""

    @abstractmethod
    def start_input(self) -> None:
        """Start microphone audio capture."""

    @abstractmethod
    def stop_input(self) -> None:
        """Stop microphone audio capture."""

    @abstractmethod
    def pause_input(self) -> None:
        """Pause microphone audio capture."""

    @abstractmethod
    def resume_input(self) -> None:
        """Resume microphone audio capture."""

    @abstractmethod
    def start_output(self) -> None:
        """Start audio playback stream."""

    @abstractmethod
    def stop_output(self) -> None:
        """Stop audio playback stream."""

    @abstractmethod
    def pause_output(self) -> None:
        """Pause audio playback stream."""

    @abstractmethod
    def resume_output(self) -> None:
        """Resume audio playback stream."""

    @abstractmethod
    def play(self, samples: Any) -> None:
        """Enqueue PCM audio samples for speaker playback."""

    @abstractmethod
    def clear_output_queue(self) -> None:
        """Flush playback queue (barge-in capability)."""

    @abstractmethod
    def subscribe(self, callback: Callable[[AudioFrame], None]) -> None:
        """Subscribe a downstream consumer to real-time AudioFrames."""

    @abstractmethod
    def unsubscribe(self, callback: Callable[[AudioFrame], None]) -> None:
        """Unsubscribe a consumer callback."""

    @abstractmethod
    def get_input_devices(self) -> list[AudioDevice]:
        """Enumerate available audio input devices."""

    @abstractmethod
    def get_output_devices(self) -> list[AudioDevice]:
        """Enumerate available audio output devices."""

    @abstractmethod
    def get_default_input_device(self) -> AudioDevice | None:
        """Get default audio input device."""

    @abstractmethod
    def get_default_output_device(self) -> AudioDevice | None:
        """Get default audio output device."""

    @abstractmethod
    def select_input_device(self, device_id: int | str | None) -> AudioDevice:
        """Select active microphone input device."""

    @abstractmethod
    def select_output_device(self, device_id: int | str | None) -> AudioDevice:
        """Select active speaker output device."""

    @abstractmethod
    def get_configuration(self) -> AudioConfiguration:
        """Get active audio configuration."""

    @abstractmethod
    def get_health_report(self) -> dict[str, Any]:
        """Collect diagnostic health report."""
