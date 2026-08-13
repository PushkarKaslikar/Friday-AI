"""Abstract interface contract for Wake Word Detector implementations."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from app.voice.audio.models import AudioFrame
from app.voice.wakeword.events import WakeWordDetected
from app.voice.wakeword.models import (
    WakeWordConfiguration,
    WakeWordEvent,
    WakeWordState,
)


class IWakeWordDetector(ABC):
    """Abstract contract enforcing WakeWordDetector service methods."""

    @property
    @abstractmethod
    def detector_state(self) -> WakeWordState:
        """Get current state of detector."""

    @property
    @abstractmethod
    def is_listening(self) -> bool:
        """True if detector is actively consuming AudioFrames."""

    @abstractmethod
    def start_listening(self) -> None:
        """Subscribe to AudioEngine frame delivery and begin ONNX inference."""

    @abstractmethod
    def stop_listening(self) -> None:
        """Unsubscribe from AudioEngine and stop frame processing."""

    @abstractmethod
    def process_frame(self, frame: AudioFrame) -> WakeWordEvent | None:
        """Process an AudioFrame for wake word ONNX inference."""

    @abstractmethod
    def reset(self) -> None:
        """Reset state machine and metrics."""

    @abstractmethod
    def subscribe_activation(
        self, callback: Callable[[WakeWordDetected], None]
    ) -> None:
        """Subscribe a listener to WakeWordDetected activation events."""

    @abstractmethod
    def unsubscribe_activation(
        self, callback: Callable[[WakeWordDetected], None]
    ) -> None:
        """Unsubscribe an activation listener callback."""

    @abstractmethod
    def get_configuration(self) -> WakeWordConfiguration:
        """Get active wake word configuration."""

    @abstractmethod
    def get_health_report(self) -> dict[str, Any]:
        """Collect diagnostic health report."""
