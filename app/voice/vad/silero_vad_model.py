"""Silero VAD ONNX Runtime model implementation.

Phase 3.4 - Voice Activity Detection & Speech Boundary Engine
"""

import os
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from app.voice.vad.models import VADConfiguration
from app.voice.vad.vad_model_interface import IVADModel

try:
    import onnxruntime as ort

    ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ort = None
    ONNXRUNTIME_AVAILABLE = False


class SileroVADModel(IVADModel):
    """Local Silero VAD model executor backed by ONNX Runtime."""

    def __init__(self, config: VADConfiguration | None = None) -> None:
        self.config = config or VADConfiguration()
        self._session: Any | None = None
        self._is_loaded: bool = False
        self._model_path: str = ""
        self._h: np.ndarray | None = None
        self._c: np.ndarray | None = None
        self._sample_rate_tensor = np.array([self.config.sample_rate], dtype=np.int64)
        self.reset_state()

    @property
    def is_loaded(self) -> bool:
        """Check if ONNX inference session is initialized."""
        return self._is_loaded and self._session is not None

    @property
    def model_path(self) -> str:
        """Path or identifier of loaded ONNX model."""
        return self._model_path

    def reset_state(self) -> None:
        """Reset internal recurrent hidden state tensors (h, c)."""
        self._h = np.zeros((2, 1, 64), dtype=np.float32)
        self._c = np.zeros((2, 1, 64), dtype=np.float32)

    def resolve_model_path(self) -> str:
        """Resolve path for silero_vad.onnx model file."""
        # 1. Check custom path setting
        if self.config.custom_model_path and os.path.exists(
            self.config.custom_model_path
        ):
            return self.config.custom_model_path

        # 2. Check local models directory (models/silero_vad.onnx)
        local_dir = Path(os.getcwd()) / "models"
        local_model = local_dir / "silero_vad.onnx"
        if local_model.exists():
            return str(local_model)

        # 3. Check openwakeword resources directory
        try:
            import openwakeword

            oww_dir = Path(openwakeword.__file__).parent / "resources" / "models"
            oww_silero = oww_dir / "silero_vad.onnx"
            if oww_silero.exists():
                return str(oww_silero)
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"SileroVADModel: openwakeword lookup skipped: {exc}")

        return str(local_model)

    def load_model(self) -> bool:
        """Load Silero VAD ONNX model session."""
        if not ONNXRUNTIME_AVAILABLE or ort is None:
            logger.error("SileroVADModel: ONNX Runtime library unavailable.")
            self._is_loaded = False
            return False

        target_path = self.resolve_model_path()
        if not os.path.exists(target_path):
            logger.error(f"SileroVADModel: Model file not found at '{target_path}'.")
            self._is_loaded = False
            return False

        try:
            opts = ort.SessionOptions()
            opts.inter_op_num_threads = 1
            opts.intra_op_num_threads = 1
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            self._session = ort.InferenceSession(
                target_path, sess_options=opts, providers=["CPUExecutionProvider"]
            )
            self._model_path = target_path
            self._is_loaded = True
            self.reset_state()
            logger.info(
                f"SileroVADModel: Successfully loaded Silero VAD model from '{target_path}'."
            )
            return True
        except Exception as exc:  # noqa: BLE001
            self._session = None
            self._is_loaded = False
            logger.error(f"SileroVADModel: Failed to load ONNX model: {exc}")
            return False

    def process_audio(self, audio_samples: Any) -> float:
        """Execute ONNX inference on float32 audio frame.

        Args:
            audio_samples: float32 array shaped (1, N) or (N,)

        Returns:
            float: Speech probability between 0.0 and 1.0.
        """
        if not self._is_loaded or self._session is None:
            return 0.0

        try:
            # Ensure input shape (1, N)
            if audio_samples.ndim == 1:
                input_data = np.expand_dims(audio_samples, axis=0).astype(np.float32)
            else:
                input_data = audio_samples.astype(np.float32)

            inputs = {
                "input": input_data,
                "sr": self._sample_rate_tensor,
                "h": self._h,
                "c": self._c,
            }

            outputs = self._session.run(None, inputs)
            prob = float(outputs[0][0][0])
            self._h = outputs[1]
            self._c = outputs[2]
            return float(np.clip(prob, 0.0, 1.0))
        except Exception as exc:  # noqa: BLE001
            logger.error(f"SileroVADModel: Inference exception: {exc}")
            return 0.0

    def unload_model(self) -> None:
        """Unload ONNX session and free memory resources."""
        self._session = None
        self._is_loaded = False
        self.reset_state()
        logger.info("SileroVADModel: Unloaded model session.")
