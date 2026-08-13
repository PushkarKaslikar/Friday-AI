"""Model Provider encapsulating OpenWakeWord model discovery, loading, and metadata inspection."""

import os
from pathlib import Path
from typing import Any

from app.logging import logger
from app.voice.wakeword.models import WakeWordConfiguration

# Try importing openwakeword runtime
try:
    import openwakeword
    from openwakeword.model import Model as OWWModel

    OPENWAKEWORD_AVAILABLE = True
except Exception:  # noqa: BLE001
    openwakeword = None
    OWWModel = None
    OPENWAKEWORD_AVAILABLE = False


class WakeWordModelProvider:
    """Manages loading, validation, and ONNX inference runtime for OpenWakeWord models.

    Local-First Privacy Guarantee:
    - Runs 100% locally in-memory via ONNX runtime. Zero cloud APIs, zero network transmission.
    """

    def __init__(self, config: WakeWordConfiguration | None = None) -> None:
        self.config = config or WakeWordConfiguration()
        self._oww_model: Any = None
        self._model_path: str = ""
        self._active_model_name: str = ""
        self._is_custom_friday_model: bool = False
        self._is_loaded: bool = False

    @property
    def is_loaded(self) -> bool:
        """True if model is loaded and ready for inference."""
        return self._is_loaded

    @property
    def active_model_name(self) -> str:
        """Active loaded wake word model name."""
        return self._active_model_name or self.config.model_name

    @property
    def model_path(self) -> str:
        """Absolute file path or identifier to active ONNX model."""
        return self._model_path

    @property
    def is_custom_friday_model(self) -> bool:
        """True if a custom 'friday.onnx' model is loaded."""
        return self._is_custom_friday_model

    def resolve_model_path(self, target_name: str | None = None) -> str:
        """Resolve path or identifier to local custom model or built-in openwakeword model."""
        name = (target_name or self.config.model_name).lower()

        # 1. Custom model path specified in settings
        if self.config.custom_model_path and os.path.exists(
            self.config.custom_model_path
        ):
            return self.config.custom_model_path

        # 2. Check local Friday models directory (models/friday.onnx)
        local_models_dir = Path(os.getcwd()) / "models"
        custom_friday = local_models_dir / f"{name}.onnx"
        if custom_friday.exists():
            return str(custom_friday)

        # 3. Fallback to openwakeword built-in pretrained model name ("hey_jarvis")
        return "hey_jarvis"

    def load_model(self) -> bool:
        """Load OpenWakeWord model into ONNX runtime."""
        if not OPENWAKEWORD_AVAILABLE or OWWModel is None:
            logger.warning("WakeWordModelProvider: OpenWakeWord library unavailable.")
            return False

        target = self.resolve_model_path()

        try:
            self._oww_model = OWWModel(
                wakeword_models=[target], inference_framework="onnx"
            )
            self._model_path = target
            self._is_custom_friday_model = (
                os.path.exists(target) and "friday" in os.path.basename(target).lower()
            )

            if self._is_custom_friday_model:
                self._active_model_name = self.config.model_name
            elif os.path.exists(target):
                self._active_model_name = os.path.basename(target).replace(".onnx", "")
            else:
                self._active_model_name = target

            self._is_loaded = True
            logger.info(
                f"WakeWordModelProvider: Successfully loaded wake word model '{self._active_model_name}' ({self._model_path})."
            )
            return True
        except Exception as exc:  # noqa: BLE001
            self._is_loaded = False
            self._oww_model = None
            logger.error(
                f"WakeWordModelProvider: Failed to load wake word model: {exc}"
            )
            return False

    def predict(self, int16_samples: Any) -> dict[str, float]:
        """Perform ONNX model inference on int16 audio frame array.

        Returns:
            dict[str, float]: Model score predictions (e.g. {'hey_jarvis': 0.85})
        """
        if not self._is_loaded or self._oww_model is None:
            return {}

        try:
            prediction = self._oww_model.predict(int16_samples)
            if isinstance(prediction, dict):
                return prediction
            if isinstance(prediction, list) and len(prediction) > 0:
                return prediction[0]
            return {}
        except Exception as exc:  # noqa: BLE001
            logger.error(f"WakeWordModelProvider: Inference exception: {exc}")
            return {}

    def unload_model(self) -> None:
        """Unload ONNX runtime model and free memory."""
        self._oww_model = None
        self._is_loaded = False
        self._model_path = ""
        logger.info("WakeWordModelProvider: Unloaded model.")
