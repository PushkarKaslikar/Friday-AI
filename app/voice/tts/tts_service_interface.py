"""Abstract interface contract for TTS service.

Phase 3.6 - Piper Local Text-to-Speech Engine
"""

from abc import ABC, abstractmethod
from collections.abc import Callable

from app.voice.tts.models import TTSConfiguration, TTSResult, TTSState


class ITTSService(ABC):
    """Abstract interface contract for TTS Service management."""

    @abstractmethod
    def speak(self, text: str, auto_play: bool = True) -> TTSResult:
        """Synthesize text and play audio through speaker output.

        Args:
            text: Text to speak
            auto_play: Automatically enqueue audio for speaker playback

        Returns:
            TTSResult: Structured TTS synthesis result.
        """

    @abstractmethod
    def synthesize(self, text: str) -> TTSResult:
        """Synthesize text to audio without automatically playing it.

        Args:
            text: Text to synthesize

        Returns:
            TTSResult: Structured TTS result containing metadata.
        """

    @abstractmethod
    def stop(self) -> None:
        """Stop current speech synthesis and flush pending playback queue (barge-in capability)."""

    @abstractmethod
    def register_callback(self, callback: Callable[[TTSResult], None]) -> None:
        """Register callback hook notified when TTS completes."""

    @abstractmethod
    def unregister_callback(self, callback: Callable[[TTSResult], None]) -> None:
        """Unregister previously registered callback hook."""

    @property
    @abstractmethod
    def tts_state(self) -> TTSState:
        """Current operational state of TTS subsystem."""

    @property
    @abstractmethod
    def tts_config(self) -> TTSConfiguration:
        """Active TTS configuration model."""

    @property
    @abstractmethod
    def is_speaking(self) -> bool:
        """Check if TTS is actively synthesizing or playing audio."""
