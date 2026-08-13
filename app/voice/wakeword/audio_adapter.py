"""Audio format converter adapting AudioFrame samples to OpenWakeWord expected input."""

import numpy as np

from app.voice.audio.models import AudioFrame


class WakeWordAudioAdapter:
    """Converts AudioFrame numpy samples to OpenWakeWord format (int16 1D numpy array).

    ZERO allocations when array formats already match.
    """

    @staticmethod
    def adapt_frame(frame: AudioFrame) -> np.ndarray:
        """Convert float32 AudioFrame numpy samples to int16 PCM numpy array."""
        samples = frame.samples
        if samples is None or len(samples) == 0:
            return np.zeros(0, dtype=np.int16)

        # 1. Flatten / squeeze to 1D array
        if len(samples.shape) > 1:
            samples = samples.squeeze()

        # 2. If already int16, return directly
        if samples.dtype == np.int16:
            return samples

        # 3. Convert float32 [-1.0, 1.0] to int16 [-32768, 32767]
        scaled = samples * 32767.0
        clipped = np.clip(scaled, -32768.0, 32767.0)
        return clipped.astype(np.int16)
