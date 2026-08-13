"""Abstract interface contract for Double-Clap Detector implementations."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from app.voice.audio.models import AudioFrame
from app.voice.clap.events import DoubleClapDetected
from app.voice.clap.models import ClapConfiguration, ClapEvent, ClapState


class IClapDetector(ABC):
    """Abstract contract enforcing ClapDetector methods decoupled from audio streaming."""

    @property
    @abstractmethod
    def state(self) -> ClapState:
        """Get current state machine state."""

    @property
    @abstractmethod
    def is_listening(self) -> bool:
        """Check if ClapDetector is actively processing AudioFrames."""

    @abstractmethod
    def start_listening(self) -> None:
        """Subscribe to AudioEngine frame delivery and begin clap processing."""

    @abstractmethod
    def stop_listening(self) -> None:
        """Unsubscribe from AudioEngine and stop clap processing."""

    @abstractmethod
    def process_frame(self, frame: AudioFrame) -> ClapEvent | None:
        """Process an AudioFrame for clap transient analysis."""

    @abstractmethod
    def reset(self) -> None:
        """Reset state machine and signal processor baseline."""

    @abstractmethod
    def subscribe_activation(
        self, callback: Callable[[DoubleClapDetected], None]
    ) -> None:
        """Subscribe a listener to DoubleClapDetected activation events."""

    @abstractmethod
    def unsubscribe_activation(
        self, callback: Callable[[DoubleClapDetected], None]
    ) -> None:
        """Unsubscribe an activation listener callback."""

    @abstractmethod
    def get_configuration(self) -> ClapConfiguration:
        """Get active clap configuration parameters."""

    @abstractmethod
    def get_health_report(self) -> dict[str, Any]:
        """Collect diagnostic health report."""
