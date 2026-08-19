"""Concrete TTS background service implementation.

Phase 3.6 - Piper Local Text-to-Speech Engine
"""

import re
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.config.manager import ConfigurationManager
from app.logging import logger
from app.services.base.service_interface import BaseService
from app.services.events.event_bus import EventBus
from app.voice.audio.audio_engine import AudioEngine
from app.voice.tts.audio_adapter import TTSAudioAdapter
from app.voice.tts.diagnostics import TTSDiagnostics
from app.voice.tts.events import (
    TTSError,
    TTSFailed,
    TTSModelLoaded,
    TTSModelUnloaded,
    TTSPlaybackCompleted,
    TTSPlaybackStarted,
    TTSStateChanged,
    TTSStopped,
    TTSSynthesisCompleted,
    TTSSynthesisStarted,
)
from app.voice.tts.metrics import TTSMetrics
from app.voice.tts.models import (
    TTSConfiguration,
    TTSResult,
    TTSState,
)
from app.voice.tts.piper_tts_provider import PiperTTSProvider
from app.voice.tts.tts_provider_interface import ITTSProvider
from app.voice.tts.tts_service_interface import ITTSService


class TTSService(BaseService, ITTSService):
    """Background service managing TTS lifecycle, synthesis queuing, speaker playback, and cancellation."""

    def __init__(
        self,
        config_manager: ConfigurationManager | None = None,
        audio_engine: AudioEngine | None = None,
        event_bus: EventBus | None = None,
        provider: ITTSProvider | None = None,
        metrics: TTSMetrics | None = None,
        diagnostics: TTSDiagnostics | None = None,
    ) -> None:
        super().__init__(name="TTSService", is_critical=False)
        self.config_manager = config_manager or ConfigurationManager()
        self.audio_engine = audio_engine or AudioEngine()
        self.event_bus = event_bus or EventBus()
        self.metrics = metrics or TTSMetrics()
        self.diagnostics = diagnostics or TTSDiagnostics(metrics=self.metrics)

        self._tts_config: TTSConfiguration = self._load_tts_configuration()
        self.provider: ITTSProvider = provider or PiperTTSProvider(
            config=self._tts_config
        )

        self._tts_state: TTSState = TTSState.DISABLED
        self._is_speaking: bool = False
        self._callbacks: set[Callable[[TTSResult], None]] = set()
        self._callbacks_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="FridayTTSWorker"
        )
        self._last_error: str | None = None

    @property
    def tts_config(self) -> TTSConfiguration:
        """Active TTS configuration model."""
        return self._tts_config

    @property
    def tts_state(self) -> TTSState:
        """Current TTS operational state."""
        return self._tts_state

    @property
    def is_speaking(self) -> bool:
        """Check if TTS is actively synthesizing or playing audio."""
        return self._is_speaking or getattr(self.audio_engine, "is_playing_audio", False)

    def _set_tts_state(self, new_state: TTSState) -> None:
        """Transition TTS state and publish EventBus notification."""
        if self._tts_state != new_state:
            prev = self._tts_state.value
            self._tts_state = new_state
            self.event_bus.publish(
                TTSStateChanged(previous_state=prev, new_state=new_state.value)
            )

    def _load_tts_configuration(self) -> TTSConfiguration:
        """Load TTS configuration from ConfigurationManager."""
        try:
            settings = self.config_manager.settings
            if hasattr(settings, "tts"):
                tts_cfg = settings.tts
                return TTSConfiguration(
                    enabled=tts_cfg.enabled,
                    voice=tts_cfg.voice,
                    language=tts_cfg.language,
                    model_path=tts_cfg.model_path,
                    config_path=tts_cfg.config_path,
                    max_text_length=tts_cfg.max_text_length,
                    auto_play=tts_cfg.auto_play,
                    use_cuda=tts_cfg.use_cuda,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"TTSService: Failed to load TTSSettings from config, using defaults: {exc}"
            )

        return TTSConfiguration()

    def _do_initialize(self) -> None:
        """Initialize TTS voice model."""
        if not self._tts_config.enabled:
            logger.info("TTSService: Subsystem disabled in settings.")
            self._set_tts_state(TTSState.DISABLED)
            return

        self._set_tts_state(TTSState.LOADING)
        success = self.provider.load_model()
        if success:
            self._set_tts_state(TTSState.READY)
            self.event_bus.publish(
                TTSModelLoaded(
                    voice_name=self._tts_config.voice,
                    sample_rate=self.provider.sample_rate,
                )
            )
            logger.info("TTSService: Successfully initialized voice model.")
        else:
            self._set_tts_state(TTSState.ERROR)
            self._last_error = "Failed to load Piper voice model"
            self.event_bus.publish(
                TTSError(error_message="Failed to load Piper voice model")
            )
            logger.error("TTSService: Initialization failed.")

    def _do_start(self) -> None:
        """Start TTS service."""
        if self._tts_config.enabled and self.provider.is_loaded:
            self._set_tts_state(TTSState.READY)

    def _do_stop(self) -> None:
        """Stop service, cancel speech and unload voice model."""
        self.stop()
        self.provider.unload_model()
        self._set_tts_state(TTSState.UNLOADED)
        self.event_bus.publish(TTSModelUnloaded())
        self._executor.shutdown(wait=False)
        logger.info("TTSService: Stopped service.")

    def _split_into_chunks(self, text: str) -> list[str]:
        """Split text into sentence chunks if exceeding max_text_length."""
        if len(text) <= self._tts_config.max_text_length:
            return [text]

        sentences = re.split(r"(?<=[.!?]) +|\n+", text)
        chunks: list[str] = []
        curr = ""

        for s in sentences:
            if len(curr) + len(s) + 1 <= self._tts_config.max_text_length:
                curr = f"{curr} {s}".strip()
            else:
                if curr:
                    chunks.append(curr)
                curr = s

        if curr:
            chunks.append(curr)

        return chunks or [text]

    def synthesize(self, text: str) -> TTSResult:
        """Synchronously synthesize text to PCM float32 audio without automatically playing it."""
        clean_text = text.strip()
        if not clean_text:
            return TTSResult(text="", status="EMPTY_INPUT")

        if not self.provider.is_loaded:
            return TTSResult(
                text=clean_text,
                status="FAILED",
                metadata={"error": "Voice model not loaded"},
            )

        chunks = self._split_into_chunks(clean_text)
        audio_parts = []
        total_duration = 0.0
        total_synth_time = 0.0

        for chunk in chunks:
            samples, _sr, res = self.provider.synthesize(chunk)
            if res.status == "SUCCESS" and len(samples) > 0:
                audio_parts.append(samples)
                total_duration += res.audio_duration_seconds
                total_synth_time += res.synthesis_time_seconds

        if not audio_parts:
            return TTSResult(text=clean_text, status="FAILED")

        rtf = round(total_synth_time / max(0.001, total_duration), 3)
        result = TTSResult(
            text=clean_text,
            audio_duration_seconds=round(total_duration, 2),
            synthesis_time_seconds=round(total_synth_time, 3),
            real_time_factor=rtf,
            voice_name=self._tts_config.voice,
            sample_rate=self.provider.sample_rate,
            status="SUCCESS",
        )
        return result

    def speak(self, text: str, auto_play: bool = True) -> TTSResult:
        """Synthesize text and play audio through speaker output."""
        clean_text = text.strip()
        if not clean_text:
            return TTSResult(text="", status="EMPTY_INPUT")

        if not self.provider.is_loaded:
            logger.warning("TTSService: Speak requested but voice model not loaded.")
            return TTSResult(
                text=clean_text,
                status="FAILED",
                metadata={"error": "Voice model not loaded"},
            )

        self._is_speaking = True
        self._set_tts_state(TTSState.SYNTHESIZING)
        self.event_bus.publish(
            TTSSynthesisStarted(text=clean_text, voice_name=self._tts_config.voice)
        )

        try:
            chunks = self._split_into_chunks(clean_text)
            overall_result = None

            for chunk in chunks:
                raw_samples, sr, res = self.provider.synthesize(chunk)
                if res.status != "SUCCESS" or len(raw_samples) == 0:
                    continue

                overall_result = res
                self.metrics.record_synthesis(
                    status=res.status,
                    audio_duration_sec=res.audio_duration_seconds,
                    synthesis_time_sec=res.synthesis_time_seconds,
                )

                self.event_bus.publish(
                    TTSSynthesisCompleted(
                        text=res.text,
                        audio_duration_seconds=res.audio_duration_seconds,
                        synthesis_time_seconds=res.synthesis_time_seconds,
                        real_time_factor=res.real_time_factor,
                        voice_name=res.voice_name,
                        sample_rate=res.sample_rate,
                    )
                )

                # Convert sample rate to AudioEngine target sample rate (16000 Hz)
                target_sr = self.audio_engine.get_configuration().sample_rate
                resampled_audio = TTSAudioAdapter.prepare_audio(
                    audio_samples=raw_samples,
                    source_sample_rate=sr,
                    target_sample_rate=target_sr,
                )

                if auto_play and self._tts_config.auto_play:
                    self._set_tts_state(TTSState.PLAYING)
                    self.event_bus.publish(
                        TTSPlaybackStarted(
                            text=chunk,
                            audio_duration_seconds=res.audio_duration_seconds,
                        )
                    )

                    # Enqueue audio into AudioEngine for speaker output
                    self.audio_engine.play(resampled_audio)
                    self.metrics.record_playback_completed()

                    self.event_bus.publish(
                        TTSPlaybackCompleted(
                            text=chunk,
                            audio_duration_seconds=res.audio_duration_seconds,
                        )
                    )

            final_res = overall_result or TTSResult(text=clean_text, status="FAILED")
            self._notify_callbacks(final_res)
            return final_res

        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
            self.metrics.record_error()
            self.event_bus.publish(TTSFailed(error_message=str(exc)))
            logger.error(f"TTSService: Speech execution error: {exc}")
            return TTSResult(
                text=clean_text,
                status="FAILED",
                metadata={"error": str(exc)},
            )
        finally:
            self._is_speaking = False
            self._set_tts_state(
                TTSState.READY if self.provider.is_loaded else TTSState.ERROR
            )

    def stop(self) -> None:
        """Stop current synthesis and flush speaker playback queue (barge-in capability)."""
        self._is_speaking = False
        self._set_tts_state(TTSState.STOPPING)

        # Flush speaker output queue in AudioEngine
        self.audio_engine.clear_output_queue()
        self.metrics.record_playback_stopped()

        self.event_bus.publish(TTSStopped(reason="User requested stop"))
        logger.info("TTSService: Speech synthesis and playback stopped.")
        self._set_tts_state(
            TTSState.READY if self.provider.is_loaded else TTSState.ERROR
        )

    def register_callback(self, callback: Callable[[TTSResult], None]) -> None:
        """Register callback for TTS events."""
        with self._callbacks_lock:
            self._callbacks.add(callback)

    def unregister_callback(self, callback: Callable[[TTSResult], None]) -> None:
        """Unregister callback."""
        with self._callbacks_lock:
            self._callbacks.discard(callback)

    def _notify_callbacks(self, result: TTSResult) -> None:
        """Invoke all registered callbacks."""
        with self._callbacks_lock:
            cbs = list(self._callbacks)

        for cb in cbs:
            try:
                cb(result)
            except Exception as exc:  # noqa: BLE001
                logger.error(f"TTSService: Callback execution exception: {exc}")

    def get_health_report(self) -> dict[str, Any]:
        """Generate diagnostic health report."""
        return self.diagnostics.get_health_report(
            service_state=self.tts_state.value,
            voice_name=self._tts_config.voice,
            model_loaded=self.provider.is_loaded,
            sample_rate=self.provider.sample_rate,
            enabled=self._tts_config.enabled,
            auto_play=self._tts_config.auto_play,
            is_speaking=self.is_speaking,
            last_error=self._last_error,
        )

    def health_check(self) -> dict[str, Any]:
        """HealthMonitor service integration hook."""
        base = super().health_check()
        base.update(self.get_health_report())
        return base
