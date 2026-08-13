"""Abstract interface contract for Speech-to-Text inference engines.

Phase 3.5 - Faster-Whisper Speech-to-Text Engine
"""

from abc import ABC, abstractmethod
from typing import Any

from app.voice.stt.models import TranscriptionResult


class ISTTEngine(ABC):
    """Abstract interface contract for local STT model implementations."""

    @abstractmethod
    def load_model(self) -> bool:
        """Load STT model into memory or GPU execution context.

        Returns:
            bool: True if model loaded successfully, False otherwise.
        """

    @abstractmethod
    def transcribe(
        self, audio_samples: Any, sample_rate: int = 16000
    ) -> TranscriptionResult:
        """Run speech-to-text transcription on PCM float32 audio samples.

        Args:
            audio_samples: float32 numpy array or audio buffer
            sample_rate: Audio sample rate in Hz (default: 16000)

        Returns:
            TranscriptionResult: Structured result object with text and timing.
        """

    @abstractmethod
    def unload_model(self) -> None:
        """Unload model session and free GPU/CPU memory."""

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if STT model is loaded and ready for transcription."""
