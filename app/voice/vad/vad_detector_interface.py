"""Abstract interface contract for Voice Activity Detector service.

Phase 3.4 - Voice Activity Detection & Speech Boundary Engine
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from app.voice.vad.models import SpeechSegment, VADState


class IVADDetector(ABC):
    """Abstract interface contract for VADDetector service."""

    @abstractmethod
    def start_listening() -> bool:
        """Start listening to AudioEngine audio frame delivery."""

    @abstractmethod
    def stop_listening() -> None:
        """Stop listening to audio frames."""

    @abstractmethod
    def add_speech_callback(
        self,
        on_started: Callable[[float, float], None] | None = None,
        on_stopped: Callable[[SpeechSegment], None] | None = None,
    ) -> None:
        """Register callbacks for speech start and speech stop events."""

    @property
    @abstractmethod
    def vad_state(self) -> VADState:
        """Get current VAD state."""

    @abstractmethod
    def get_health_report(self) -> dict[str, Any]:
        """Get structured health report for VAD subsystem."""
