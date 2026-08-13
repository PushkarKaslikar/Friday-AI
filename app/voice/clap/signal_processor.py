"""Audio signal processing algorithm for local deterministic clap impulse recognition."""

import numpy as np

from app.voice.audio.models import AudioFrame
from app.voice.clap.models import ClapConfiguration, ClapEvent


class ClapSignalProcessor:
    """Local, deterministic signal processor analyzing transient attack, energy ratio, and adaptive noise floor.

    ZERO Cloud Calls. ZERO LLMs. ZERO Heavy Neural Models.
    """

    def __init__(self, config: ClapConfiguration | None = None) -> None:
        self.config = config or ClapConfiguration()
        self._noise_floor_energy: float = 0.001
        self._alpha: float = 0.05  # Adaptive noise floor smoothing factor

    @property
    def noise_floor(self) -> float:
        """Current estimated background noise floor RMS energy."""
        return self._noise_floor_energy

    def reset(self) -> None:
        """Reset noise floor baseline to initial default state."""
        self._noise_floor_energy = 0.001

    def process_frame(self, frame: AudioFrame) -> ClapEvent | None:
        """Analyze audio frame samples and return ClapEvent if impulse matches clap characteristics."""
        samples = frame.samples
        if samples is None or len(samples) == 0:
            return None

        # Ensure 1D float32 array
        if len(samples.shape) > 1:
            samples = samples.squeeze()

        sample_rate = frame.sample_rate

        # 1. Calculate Peak Amplitude & RMS Energy
        peak_amp = float(np.max(np.abs(samples)))
        rms_energy = float(np.sqrt(np.mean(samples**2)))

        # Update running adaptive noise floor if frame energy is relatively quiet
        if rms_energy < (self._noise_floor_energy * 3.0):
            self._noise_floor_energy = (
                1.0 - self._alpha
            ) * self._noise_floor_energy + self._alpha * max(1e-5, rms_energy)

        # 2. Check Minimum Peak Amplitude Threshold
        if peak_amp < self.config.min_peak_amplitude:
            return None

        # 3. Check Energy Threshold Relative to Noise Floor
        required_energy = (
            self._noise_floor_energy * self.config.energy_threshold_multiplier
        )
        if rms_energy < required_energy:
            return None

        # 4. Attack / Crest Factor Analysis (Peak to RMS Ratio)
        # Claps feature a sharp transient onset resulting in high peak-to-RMS ratios (> 3.0)
        crest_factor = peak_amp / max(1e-6, rms_energy)
        if crest_factor < 2.5:
            return None

        # 5. Impulse Duration Estimate
        # Count consecutive samples exceeding 30% of peak amplitude
        threshold_level = peak_amp * 0.3
        above_threshold_indices = np.where(np.abs(samples) >= threshold_level)[0]
        if len(above_threshold_indices) == 0:
            return None

        first_sample_idx = above_threshold_indices[0]
        last_sample_idx = above_threshold_indices[-1]
        impulse_sample_count = last_sample_idx - first_sample_idx + 1
        duration_ms = (impulse_sample_count / float(sample_rate)) * 1000.0

        if (
            duration_ms < self.config.min_duration_ms
            or duration_ms > self.config.max_duration_ms
        ):
            return None

        # 6. Compute Clap Confidence Score (0.0 to 1.0)
        # Combine normalized peak score, energy-over-noise ratio, and crest factor
        amp_score = min(1.0, peak_amp / 0.8)
        energy_ratio = rms_energy / max(1e-5, self._noise_floor_energy)
        ratio_score = min(1.0, energy_ratio / 15.0)
        crest_score = min(1.0, crest_factor / 6.0)

        confidence = round(0.4 * amp_score + 0.3 * ratio_score + 0.3 * crest_score, 3)

        if confidence < self.config.confidence_threshold:
            return None

        quality = (
            "HIGH" if confidence >= 0.85 else ("MEDIUM" if confidence >= 0.7 else "LOW")
        )

        return ClapEvent(
            timestamp=frame.timestamp,
            confidence=confidence,
            peak_amplitude=round(peak_amp, 4),
            energy=round(rms_energy, 6),
            duration=round(duration_ms, 2),
            signal_quality=quality,
            metadata={
                "crest_factor": round(crest_factor, 2),
                "noise_floor": round(self._noise_floor_energy, 6),
                "sample_rate": sample_rate,
            },
        )
