"""Faster-Whisper local Speech-to-Text engine implementation.

Phase 3.5 - Faster-Whisper Speech-to-Text Engine
"""

import time
from typing import Any

import numpy as np

from app.logging import logger
from app.voice.stt.models import (
    STTConfiguration,
    TranscriptionResult,
    TranscriptSegment,
)
from app.voice.stt.stt_engine_interface import ISTTEngine

try:
    import faster_whisper

    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    faster_whisper = None
    FASTER_WHISPER_AVAILABLE = False


class FasterWhisperSTTEngine(ISTTEngine):
    """Local Speech-to-Text engine backed by Faster-Whisper (ctranslate2)."""

    def __init__(self, config: STTConfiguration | None = None) -> None:
        self.config = config or STTConfiguration()
        self._model: Any | None = None
        self._is_loaded: bool = False
        self._actual_device: str = "cpu"
        self._actual_compute_type: str = "int8"
        self._load_time_seconds: float = 0.0

    @property
    def is_loaded(self) -> bool:
        """Check if Whisper model is loaded."""
        return self._is_loaded and self._model is not None

    @property
    def actual_device(self) -> str:
        """Resolved compute device ('cpu' or 'cuda')."""
        return self._actual_device

    @property
    def actual_compute_type(self) -> str:
        """Resolved quantization compute type."""
        return self._actual_compute_type

    def _resolve_device_and_compute(self) -> tuple[str, str]:
        """Determine optimal device and compute_type based on configuration and hardware."""
        target_device = self.config.device.lower()
        target_compute = self.config.compute_type.lower()

        # Check CUDA availability
        cuda_available = False
        try:
            import torch

            cuda_available = torch.cuda.is_available()
        except ImportError:
            # Check via ctranslate2
            try:
                import ctranslate2

                cuda_available = "cuda" in ctranslate2.get_supported_devices()
            except Exception:  # noqa: BLE001
                cuda_available = False

        if target_device in ("auto", "cuda") and cuda_available:
            device = "cuda"
            compute = "float16" if target_compute == "auto" else target_compute
        else:
            if target_device == "cuda" and not cuda_available:
                logger.warning(
                    "FasterWhisperSTTEngine: CUDA requested but unavailable. Falling back to CPU."
                )
            device = "cpu"
            compute = (
                "int8" if target_compute in ("auto", "float16") else target_compute
            )

        return device, compute

    def load_model(self) -> bool:
        """Load Faster-Whisper model into memory/GPU context."""
        if not FASTER_WHISPER_AVAILABLE or faster_whisper is None:
            logger.error("FasterWhisperSTTEngine: faster-whisper package unavailable.")
            self._is_loaded = False
            return False

        device, compute_type = self._resolve_device_and_compute()
        model_id = self.config.custom_model_path or self.config.model_name
        t_start = time.perf_counter()

        try:
            logger.info(
                f"FasterWhisperSTTEngine: Loading model '{model_id}' on device '{device}' ({compute_type})..."
            )
            self._model = faster_whisper.WhisperModel(
                model_size_or_path=model_id,
                device=device,
                compute_type=compute_type,
            )
            self._actual_device = device
            self._actual_compute_type = compute_type
            self._load_time_seconds = round(time.perf_counter() - t_start, 3)
            self._is_loaded = True
            logger.info(
                f"FasterWhisperSTTEngine: Model '{model_id}' loaded successfully in {self._load_time_seconds}s."
            )
            return True
        except Exception as exc:  # noqa: BLE001
            # Attempt CPU fallback if CUDA failed
            if device == "cuda":
                logger.warning(
                    f"FasterWhisperSTTEngine: CUDA model load failed ({exc}). Retrying on CPU..."
                )
                try:
                    self._model = faster_whisper.WhisperModel(
                        model_size_or_path=model_id,
                        device="cpu",
                        compute_type="int8",
                    )
                    self._actual_device = "cpu"
                    self._actual_compute_type = "int8"
                    self._load_time_seconds = round(time.perf_counter() - t_start, 3)
                    self._is_loaded = True
                    logger.info(
                        f"FasterWhisperSTTEngine: Fallback CPU model loaded in {self._load_time_seconds}s."
                    )
                    return True
                except Exception as fallback_exc:  # noqa: BLE001
                    logger.error(
                        f"FasterWhisperSTTEngine: CPU fallback model load failed: {fallback_exc}"
                    )

            self._model = None
            self._is_loaded = False
            logger.error(f"FasterWhisperSTTEngine: Failed to load model: {exc}")
            return False

    def transcribe(
        self, audio_samples: Any, sample_rate: int = 16000
    ) -> TranscriptionResult:
        """Transcribe PCM float32 audio samples to text.

        Args:
            audio_samples: float32 numpy array
            sample_rate: Audio sample rate in Hz (default: 16000)

        Returns:
            TranscriptionResult: Structured result containing transcribed text and metadata.
        """
        if not self._is_loaded or self._model is None:
            return TranscriptionResult(
                text="",
                status="FAILED",
                metadata={"error": "Model not loaded"},
            )

        # Convert to 1D float32 numpy array
        if not isinstance(audio_samples, np.ndarray):
            audio_samples = np.array(audio_samples, dtype=np.float32)
        elif audio_samples.dtype != np.float32:
            audio_samples = audio_samples.astype(np.float32)

        if audio_samples.ndim > 1:
            audio_samples = audio_samples.squeeze()

        audio_len = len(audio_samples)
        duration_sec = round(audio_len / max(1, sample_rate), 3)

        # Minimum audio duration check (< 100ms)
        if duration_sec < 0.1:
            return TranscriptionResult(
                text="",
                duration_seconds=duration_sec,
                status="TOO_SHORT",
                model_name=self.config.model_name,
                device=self._actual_device,
                compute_type=self._actual_compute_type,
            )

        t_start = time.perf_counter()
        try:
            kwargs: dict[str, Any] = {
                "beam_size": self.config.beam_size,
                "word_timestamps": self.config.word_timestamps,
                "vad_filter": self.config.vad_filter,
            }
            if self.config.language:
                kwargs["language"] = self.config.language

            segments_generator, info = self._model.transcribe(audio_samples, **kwargs)

            # Consume generator
            segments_list: list[TranscriptSegment] = []
            text_parts: list[str] = []

            for seg in segments_generator:
                clean_text = seg.text.strip()
                if clean_text:
                    text_parts.append(clean_text)
                    segments_list.append(
                        TranscriptSegment(
                            start=round(seg.start, 2),
                            end=round(seg.end, 2),
                            text=clean_text,
                            confidence=round(getattr(seg, "avg_logprob", 0.0), 3),
                        )
                    )

            proc_time = round(time.perf_counter() - t_start, 3)
            full_text = " ".join(text_parts).strip()
            rtf = round(proc_time / max(0.001, duration_sec), 3)
            status = "SUCCESS" if full_text else "EMPTY"

            detected_lang = getattr(info, "language", self.config.language or "en")
            detected_prob = round(getattr(info, "language_probability", 1.0), 3)

            logger.info(
                f"FasterWhisperSTTEngine: Transcribed {duration_sec}s audio in {proc_time}s (RTF: {rtf}) -> '{full_text}'"
            )

            return TranscriptionResult(
                text=full_text,
                language=detected_lang,
                language_probability=detected_prob,
                duration_seconds=duration_sec,
                processing_time_seconds=proc_time,
                real_time_factor=rtf,
                segments=segments_list,
                model_name=self.config.model_name,
                device=self._actual_device,
                compute_type=self._actual_compute_type,
                status=status,
            )
        except Exception as exc:  # noqa: BLE001
            proc_time = round(time.perf_counter() - t_start, 3)
            logger.error(f"FasterWhisperSTTEngine: Transcription exception: {exc}")
            return TranscriptionResult(
                text="",
                duration_seconds=duration_sec,
                processing_time_seconds=proc_time,
                status="FAILED",
                model_name=self.config.model_name,
                device=self._actual_device,
                compute_type=self._actual_compute_type,
                metadata={"error": str(exc)},
            )

    def unload_model(self) -> None:
        """Unload Faster-Whisper model from memory."""
        self._model = None
        self._is_loaded = False
        logger.info("FasterWhisperSTTEngine: Unloaded model session.")
