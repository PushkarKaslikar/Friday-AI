"""Piper TTS local model provider implementation.

Phase 3.6 - Piper Local Text-to-Speech Engine
"""

import time
from pathlib import Path
from typing import Any

import numpy as np

from app.logging import logger
from app.voice.tts.models import TTSConfiguration, TTSResult
from app.voice.tts.tts_provider_interface import ITTSProvider

try:
    import piper

    PIPER_AVAILABLE = True
except ImportError:
    piper = None
    PIPER_AVAILABLE = False


class PiperTTSProvider(ITTSProvider):
    """Local Text-to-Speech provider backed by Piper (piper-tts)."""

    def __init__(self, config: TTSConfiguration | None = None) -> None:
        self.config = config or TTSConfiguration()
        self._voice: Any | None = None
        self._is_loaded: bool = False
        self._sample_rate: int = 22050
        self._load_time_seconds: float = 0.0
        self._resolved_model_path: str | None = None

    @property
    def is_loaded(self) -> bool:
        """Check if Piper voice model is loaded."""
        return self._is_loaded and self._voice is not None

    @property
    def sample_rate(self) -> int:
        """Native sample rate of loaded voice model."""
        return self._sample_rate

    @property
    def model_path(self) -> str | None:
        """Resolved file path to current Piper voice .onnx model."""
        return self._resolved_model_path

    def _resolve_model_and_config_paths(self) -> tuple[Path, Path]:
        """Locate or download local Piper female voice model (.onnx and .onnx.json)."""
        voice_name = self.config.voice

        # 1. Custom model path specified in settings
        if self.config.model_path:
            m_path = Path(self.config.model_path)
            c_path = (
                Path(self.config.config_path)
                if self.config.config_path
                else Path(f"{self.config.model_path}.json")
            )
            if m_path.exists():
                return m_path, c_path

        # 2. Local workspace models/tts directory
        local_dir = Path("models") / "tts"
        local_model = local_dir / f"{voice_name}.onnx"
        local_config = local_dir / f"{voice_name}.onnx.json"
        if local_model.exists():
            return local_model, local_config

        # 3. HuggingFace hub automatic download fallback
        try:
            from huggingface_hub import hf_hub_download

            logger.info(
                f"PiperTTSProvider: Downloading voice model '{voice_name}' from rhasspy/piper-voices..."
            )
            # Default female voice mapping: en_US-amy-medium -> en/en_US/amy/medium/en_US-amy-medium.onnx
            lang_prefix, speaker, quality = voice_name.split("-")
            lang_code = lang_prefix.split("_")[0]
            rel_path = (
                f"{lang_code}/{lang_prefix}/{speaker}/{quality}/{voice_name}.onnx"
            )

            downloaded_model = hf_hub_download(
                repo_id="rhasspy/piper-voices",
                filename=rel_path,
            )
            downloaded_config = hf_hub_download(
                repo_id="rhasspy/piper-voices",
                filename=f"{rel_path}.json",
            )
            return Path(downloaded_model), Path(downloaded_config)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"PiperTTSProvider: HuggingFace model resolution failed for '{voice_name}': {exc}"
            )

        return local_model, local_config

    def load_model(self) -> bool:
        """Load Piper voice model into memory."""
        if not PIPER_AVAILABLE or piper is None:
            logger.error("PiperTTSProvider: piper-tts package unavailable.")
            self._is_loaded = False
            return False

        t_start = time.perf_counter()
        try:
            model_path, config_path = self._resolve_model_and_config_paths()
            if not model_path.exists():
                logger.error(
                    f"PiperTTSProvider: Voice model file not found at '{model_path}'."
                )
                self._is_loaded = False
                return False

            logger.info(f"PiperTTSProvider: Loading Piper voice from '{model_path}'...")
            self._voice = piper.PiperVoice.load(
                model_path=str(model_path),
                config_path=str(config_path) if config_path.exists() else None,
                use_cuda=self.config.use_cuda,
            )
            self._sample_rate = getattr(self._voice.config, "sample_rate", 22050)
            self._resolved_model_path = str(model_path)
            self._load_time_seconds = round(time.perf_counter() - t_start, 3)
            self._is_loaded = True

            logger.info(
                f"PiperTTSProvider: Successfully loaded voice '{self.config.voice}' "
                f"({self._sample_rate}Hz) in {self._load_time_seconds}s."
            )
            return True
        except Exception as exc:  # noqa: BLE001
            self._voice = None
            self._is_loaded = False
            logger.error(f"PiperTTSProvider: Failed to load Piper voice: {exc}")
            return False

    def synthesize(self, text: str) -> tuple[np.ndarray, int, TTSResult]:
        """Synthesize text to float32 PCM numpy audio array."""
        if not self._is_loaded or self._voice is None:
            return (
                np.zeros(0, dtype=np.float32),
                self._sample_rate,
                TTSResult(
                    text=text,
                    status="FAILED",
                    metadata={"error": "Voice model not loaded"},
                ),
            )

        clean_text = text.strip()
        if not clean_text:
            return (
                np.zeros(0, dtype=np.float32),
                self._sample_rate,
                TTSResult(text="", status="EMPTY_INPUT"),
            )

        t_start = time.perf_counter()
        try:
            chunks = list(self._voice.synthesize(clean_text))
            if not chunks:
                proc_time = round(time.perf_counter() - t_start, 3)
                return (
                    np.zeros(0, dtype=np.float32),
                    self._sample_rate,
                    TTSResult(
                        text=clean_text,
                        synthesis_time_seconds=proc_time,
                        status="EMPTY_INPUT",
                    ),
                )

            # Concatenate float32 audio arrays from chunks
            float_chunks = [
                c.audio_float_array for c in chunks if hasattr(c, "audio_float_array")
            ]
            if float_chunks:
                audio_samples = np.concatenate(float_chunks, axis=0).astype(np.float32)
            else:
                # Convert int16 bytes if float_array unavailable
                raw_bytes = b"".join(c.audio_int16_bytes for c in chunks)
                int_samples = np.frombuffer(raw_bytes, dtype=np.int16)
                audio_samples = (int_samples / 32768.0).astype(np.float32)

            proc_time = round(time.perf_counter() - t_start, 3)
            duration_sec = round(len(audio_samples) / max(1, self._sample_rate), 3)
            rtf = round(proc_time / max(0.001, duration_sec), 3)

            logger.info(
                f"PiperTTSProvider: Synthesized '{clean_text[:40]}...' ({duration_sec}s audio) "
                f"in {proc_time}s (RTF: {rtf})"
            )

            result = TTSResult(
                text=clean_text,
                audio_duration_seconds=duration_sec,
                synthesis_time_seconds=proc_time,
                real_time_factor=rtf,
                voice_name=self.config.voice,
                sample_rate=self._sample_rate,
                status="SUCCESS",
            )
            return audio_samples, self._sample_rate, result

        except Exception as exc:  # noqa: BLE001
            proc_time = round(time.perf_counter() - t_start, 3)
            logger.error(f"PiperTTSProvider: Synthesis exception: {exc}")
            return (
                np.zeros(0, dtype=np.float32),
                self._sample_rate,
                TTSResult(
                    text=clean_text,
                    synthesis_time_seconds=proc_time,
                    status="FAILED",
                    metadata={"error": str(exc)},
                ),
            )

    def unload_model(self) -> None:
        """Unload Piper voice model from memory."""
        self._voice = None
        self._is_loaded = False
        logger.info("PiperTTSProvider: Unloaded voice model session.")
