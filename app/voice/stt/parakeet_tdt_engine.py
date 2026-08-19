"""NVIDIA Parakeet-TDT-0.6B-v3 local Speech-to-Text engine implementation.

Provides high-throughput multilingual automatic speech recognition powered by NVIDIA's
FastConformer-TDT architecture using Hugging Face Transformers.
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
    import torch
    import transformers
    from transformers import AutoProcessor, ParakeetForTDT

    PARAKEET_TRANSFORMERS_AVAILABLE = True
except ImportError:
    torch = None  # type: ignore
    transformers = None  # type: ignore
    AutoProcessor = None  # type: ignore
    ParakeetForTDT = None  # type: ignore
    PARAKEET_TRANSFORMERS_AVAILABLE = False


class ParakeetTDTSTTEngine(ISTTEngine):
    """Local Speech-to-Text engine backed by NVIDIA Parakeet-TDT-0.6B-v3."""

    DEFAULT_MODEL_ID = "nvidia/parakeet-tdt-0.6b-v3"

    def __init__(self, config: STTConfiguration | None = None) -> None:
        self.config = config or STTConfiguration()
        self._model: Any | None = None
        self._processor: Any | None = None
        self._is_loaded: bool = False
        self._actual_device: str = "cpu"
        self._actual_compute_type: str = "float32"
        self._load_time_seconds: float = 0.0

    @property
    def is_loaded(self) -> bool:
        """Check if Parakeet-TDT model is loaded and ready."""
        return self._is_loaded and self._model is not None

    @property
    def actual_device(self) -> str:
        """Resolved compute execution device ('cpu' or 'cuda')."""
        return self._actual_device

    @property
    def actual_compute_type(self) -> str:
        """Resolved compute precision ('float16' or 'float32')."""
        return self._actual_compute_type

    def _resolve_device_and_dtype(self) -> tuple[str, Any]:
        """Determine device and torch dtype based on settings and available hardware."""
        target_device = self.config.device.lower()
        cuda_available = False

        if torch is not None:
            try:
                cuda_available = torch.cuda.is_available()
            except Exception:  # noqa: BLE001
                cuda_available = False

        if target_device in ("auto", "cuda") and cuda_available:
            device = "cuda"
            dtype = torch.float16 if torch else None
            compute_str = "float16"
        else:
            if target_device == "cuda" and not cuda_available:
                logger.warning(
                    "ParakeetTDTSTTEngine: CUDA requested but unavailable. Falling back to CPU."
                )
            device = "cpu"
            dtype = torch.float32 if torch else None
            compute_str = "float32"

        return device, (dtype, compute_str)

    def load_model(self) -> bool:
        """Load NVIDIA Parakeet-TDT processor and weights into memory/GPU."""
        if not PARAKEET_TRANSFORMERS_AVAILABLE:
            logger.error(
                "ParakeetTDTSTTEngine: transformers/torch/librosa packages are unavailable."
            )
            self._is_loaded = False
            return False

        device, (dtype, compute_str) = self._resolve_device_and_dtype()
        model_id = (
            self.config.custom_model_path
            or (self.config.model_name if "parakeet" in self.config.model_name.lower() else self.DEFAULT_MODEL_ID)
        )
        t_start = time.perf_counter()

        try:
            logger.info(
                f"ParakeetTDTSTTEngine: Loading model '{model_id}' on device '{device}' ({compute_str})..."
            )

            self._processor = AutoProcessor.from_pretrained(model_id)
            self._model = ParakeetForTDT.from_pretrained(
                model_id,
                torch_dtype=dtype,
                low_cpu_mem_usage=True,
            )

            if device == "cuda" and torch is not None:
                self._model = self._model.to("cuda")

            self._model.eval()

            self._actual_device = device
            self._actual_compute_type = compute_str
            self._load_time_seconds = round(time.perf_counter() - t_start, 3)
            self._is_loaded = True

            logger.info(
                f"ParakeetTDTSTTEngine: Model '{model_id}' loaded successfully in {self._load_time_seconds}s."
            )
            return True

        except Exception as exc:  # noqa: BLE001
            # Attempt CPU fallback if CUDA load failed
            if device == "cuda":
                logger.warning(
                    f"ParakeetTDTSTTEngine: CUDA model load failed ({exc}). Retrying on CPU..."
                )
                try:
                    self._processor = AutoProcessor.from_pretrained(model_id)
                    self._model = ParakeetForTDT.from_pretrained(
                        model_id,
                        torch_dtype=torch.float32,
                        low_cpu_mem_usage=True,
                    )
                    self._model.eval()
                    self._actual_device = "cpu"
                    self._actual_compute_type = "float32"
                    self._load_time_seconds = round(time.perf_counter() - t_start, 3)
                    self._is_loaded = True
                    logger.info(
                        f"ParakeetTDTSTTEngine: Fallback CPU model loaded in {self._load_time_seconds}s."
                    )
                    return True
                except Exception as fallback_exc:  # noqa: BLE001
                    logger.error(
                        f"ParakeetTDTSTTEngine: CPU fallback model load failed: {fallback_exc}"
                    )

            logger.error(f"ParakeetTDTSTTEngine: Failed to load model '{model_id}': {exc}")
            self._is_loaded = False
            return False

    def transcribe(
        self, audio_samples: Any, sample_rate: int = 16000
    ) -> TranscriptionResult:
        """Run speech-to-text inference on PCM float32 audio samples.

        Args:
            audio_samples: float32 numpy array or sequence of audio samples.
            sample_rate: Sample rate in Hz (default: 16000).

        Returns:
            TranscriptionResult: Structured result object with transcribed text.
        """
        if not self.is_loaded:
            logger.warning("ParakeetTDTSTTEngine: Transcribe called but model is not loaded.")
            return TranscriptionResult(
                text="",
                status="FAILED",
                metadata={"error": "Parakeet model not loaded"},
            )

        t_start = time.perf_counter()

        try:
            # Ensure float32 1D numpy array
            if not isinstance(audio_samples, np.ndarray):
                audio_np = np.array(audio_samples, dtype=np.float32)
            else:
                audio_np = audio_samples.astype(np.float32)

            if audio_np.ndim > 1:
                audio_np = audio_np.mean(axis=1)

            duration_sec = len(audio_np) / float(sample_rate)
            if duration_sec < 0.1:
                return TranscriptionResult(
                    text="",
                    duration_seconds=duration_sec,
                    status="TOO_SHORT",
                )

            # Process audio through ParakeetProcessor
            inputs = self._processor(
                audio_np,
                sampling_rate=sample_rate,
                return_tensors="pt",
            )

            if self._actual_device == "cuda" and torch is not None:
                inputs = {k: v.to("cuda") for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._model(**inputs)
                logits = outputs.logits
                predicted_ids = torch.argmax(logits, dim=-1)
                transcription = self._processor.batch_decode(predicted_ids)[0]

            clean_text = transcription.strip()
            proc_time = round(time.perf_counter() - t_start, 3)
            rtf = round(proc_time / max(duration_sec, 0.001), 3)

            logger.info(
                f"ParakeetTDTSTTEngine: Transcribed {duration_sec:.2f}s audio in {proc_time}s "
                f"(RTF: {rtf}) -> '{clean_text}'"
            )

            return TranscriptionResult(
                text=clean_text,
                language="en",
                language_probability=1.0,
                duration_seconds=duration_sec,
                processing_time_seconds=proc_time,
                real_time_factor=rtf,
                model_name=self.config.model_name or self.DEFAULT_MODEL_ID,
                device=self._actual_device,
                compute_type=self._actual_compute_type,
                status="SUCCESS" if clean_text else "EMPTY",
            )

        except Exception as exc:  # noqa: BLE001
            proc_time = round(time.perf_counter() - t_start, 3)
            logger.error(f"ParakeetTDTSTTEngine: Transcription failed: {exc}")
            return TranscriptionResult(
                text="",
                processing_time_seconds=proc_time,
                status="FAILED",
                metadata={"error": str(exc)},
            )

    def unload_model(self) -> None:
        """Unload Parakeet-TDT model and free GPU/CPU memory."""
        self._model = None
        self._processor = None
        self._is_loaded = False

        if torch is not None and torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
            except Exception:  # noqa: BLE001
                pass

        logger.info("ParakeetTDTSTTEngine: Unloaded model successfully.")
