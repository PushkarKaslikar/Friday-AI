"""Abstract interface contract for STT service.

Phase 3.5 - Faster-Whisper Speech-to-Text Engine
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from app.voice.stt.models import STTConfiguration, STTState, TranscriptionResult


class ISTTService(ABC):
    """Abstract interface contract for STT Service management."""

    @abstractmethod
    def start_listening(self) -> None:
        """Enable speech boundary event listening and audio collection."""

    @abstractmethod
    def stop_listening(self) -> None:
        """Disable speech boundary event listening."""

    @abstractmethod
    def transcribe_audio(
        self, audio_samples: Any, sample_rate: int = 16000
    ) -> TranscriptionResult:
        """Synchronously or asynchronously transcribe PCM float32 audio samples.

        Returns:
            TranscriptionResult: Structured transcription result.
        """

    @abstractmethod
    def register_callback(
        self, callback: Callable[[TranscriptionResult], None]
    ) -> None:
        """Register callback hook notified when a transcription completes."""

    @abstractmethod
    def unregister_callback(
        self, callback: Callable[[TranscriptionResult], None]
    ) -> None:
        """Unregister previously registered callback hook."""

    @property
    @abstractmethod
    def stt_state(self) -> STTState:
        """Current operational state of STT subsystem."""

    @property
    @abstractmethod
    def stt_config(self) -> STTConfiguration:
        """Active STT configuration model."""
