"""Abstract interface contract for Voice Activity Detection models.

Phase 3.4 - Voice Activity Detection & Speech Boundary Engine
"""

from abc import ABC, abstractmethod
from typing import Any


class IVADModel(ABC):
    """Abstract interface contract for local VAD model implementations."""

    @abstractmethod
    def load_model(self) -> bool:
        """Load model into runtime environment.

        Returns:
            bool: True if loaded successfully, False otherwise.
        """

    @abstractmethod
    def process_audio(self, audio_samples: Any) -> float:
        """Run VAD inference on input audio frame.

        Args:
            audio_samples: Formatted float32 numpy array or tensor frame.

        Returns:
            float: Speech probability between 0.0 and 1.0.
        """

    @abstractmethod
    def reset_state(self) -> None:
        """Reset internal recurrent hidden state tensors."""

    @abstractmethod
    def unload_model(self) -> None:
        """Unload model session and free memory resources."""

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if model is initialized and ready for inference."""
