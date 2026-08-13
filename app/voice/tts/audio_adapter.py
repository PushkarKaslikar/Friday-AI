"""Audio adapter converting Piper TTS sample rate to AudioEngine target sample rate.

Phase 3.6 - Piper Local Text-to-Speech Engine
"""

import numpy as np
import scipy.signal as sp

from app.logging import logger


class TTSAudioAdapter:
    """Converts PCM float32 audio samples between sample rates using Scipy resample_poly."""

    @staticmethod
    def prepare_audio(
        audio_samples: np.ndarray,
        source_sample_rate: int,
        target_sample_rate: int = 16000,
    ) -> np.ndarray:
        """Resample audio samples to match target AudioEngine output sample rate.

        Args:
            audio_samples: float32 numpy array
            source_sample_rate: Native Piper voice sample rate in Hz (e.g. 22050)
            target_sample_rate: AudioEngine target sample rate in Hz (default: 16000)

        Returns:
            np.ndarray: Resampled float32 PCM audio array.
        """
        if not isinstance(audio_samples, np.ndarray):
            audio_samples = np.array(audio_samples, dtype=np.float32)
        elif audio_samples.dtype != np.float32:
            audio_samples = audio_samples.astype(np.float32)

        if audio_samples.ndim > 1:
            audio_samples = audio_samples.squeeze()

        if len(audio_samples) == 0:
            return audio_samples

        if source_sample_rate == target_sample_rate:
            return audio_samples

        try:
            resampled = sp.resample_poly(
                audio_samples,
                up=target_sample_rate,
                down=source_sample_rate,
            ).astype(np.float32)
            return resampled
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"TTSAudioAdapter: Poly resampling failed ({exc}), returning raw audio."
            )
            return audio_samples
