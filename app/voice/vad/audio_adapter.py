"""Audio format adapter for Silero Voice Activity Detection.

Phase 3.4 - Voice Activity Detection & Speech Boundary Engine
"""

import numpy as np
from loguru import logger

from app.voice.audio.models import AudioFrame


class VADAudioAdapter:
    """Adapts Phase 3.1 AudioFrame PCM data to Silero VAD tensor format."""

    @staticmethod
    def prepare_samples(frame: AudioFrame) -> np.ndarray:
        """Convert AudioFrame to float32 numpy array formatted (1, N).

        Args:
            frame: Input AudioFrame from AudioEngine subscription.

        Returns:
            np.ndarray: float32 array of shape (1, N).
        """
        try:
            samples = frame.samples
            if samples is None or len(samples) == 0:
                return np.zeros((1, 512), dtype=np.float32)

            # Convert to float32 numpy array
            if not isinstance(samples, np.ndarray):
                samples = np.array(samples, dtype=np.float32)
            elif samples.dtype != np.float32:
                samples = samples.astype(np.float32)

            # Handle multi-channel audio (mix to mono)
            if samples.ndim > 1:
                samples = np.mean(samples, axis=1)

            # Ensure 2D shape (1, N)
            return np.expand_dims(samples, axis=0)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"VADAudioAdapter: Error formatting samples: {exc}")
            return np.zeros((1, 512), dtype=np.float32)
