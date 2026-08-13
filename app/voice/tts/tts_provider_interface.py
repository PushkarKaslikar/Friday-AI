"""Abstract interface contract for Text-to-Speech model providers.

Phase 3.6 - Piper Local Text-to-Speech Engine
"""

from abc import ABC, abstractmethod

import numpy as np

from app.voice.tts.models import TTSResult


class ITTSProvider(ABC):
    """Abstract interface contract for local TTS engine providers (e.g. Piper)."""

    @abstractmethod
    def load_model(self) -> bool:
        """Load voice model into memory context.

        Returns:
            bool: True if model loaded successfully, False otherwise.
        """

    @abstractmethod
    def synthesize(self, text: str) -> tuple[np.ndarray, int, TTSResult]:
        """Synthesize text input to float32 PCM audio samples.

        Args:
            text: Input text string

        Returns:
            tuple[np.ndarray, int, TTSResult]: (audio_samples, sample_rate, tts_result)
        """

    @abstractmethod
    def unload_model(self) -> None:
        """Unload voice model and free memory resources."""

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if voice model is loaded and ready for synthesis."""

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """Native audio sample rate of the loaded voice model in Hz."""
