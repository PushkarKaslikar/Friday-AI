"""Concrete STT background service implementation.

Phase 3.5 - Faster-Whisper Speech-to-Text Engine
"""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.config.manager import ConfigurationManager
from app.logging import logger
from app.services.base.service_interface import BaseService
from app.services.events.event_bus import EventBus
from app.voice.audio.audio_engine import AudioEngine
from app.voice.audio.models import AudioFrame
from app.voice.stt.diagnostics import STTDiagnostics
from app.voice.stt.events import (
    STTError,
    STTModelLoaded,
    STTModelUnloaded,
    STTStateChanged,
    TranscriptionCompleted,
    TranscriptionFailed,
    TranscriptionStarted,
)
from app.voice.stt.faster_whisper_engine import FasterWhisperSTTEngine
from app.voice.stt.metrics import STTMetrics
from app.voice.stt.models import (
    STTConfiguration,
    STTState,
    TranscriptionResult,
)
from app.voice.stt.speech_buffer import SpeechSegmentBuffer
from app.voice.stt.stt_engine_interface import ISTTEngine
from app.voice.stt.stt_service_interface import ISTTService


class STTService(BaseService, ISTTService):
    """Background service managing STT lifecycle, audio collection, and non-blocking transcription."""

    def __init__(
        self,
        config_manager: ConfigurationManager | None = None,
        audio_engine: AudioEngine | None = None,
        event_bus: EventBus | None = None,
        engine: ISTTEngine | None = None,
        metrics: STTMetrics | None = None,
        diagnostics: STTDiagnostics | None = None,
    ) -> None:
        super().__init__(name="STTService", is_critical=False)
        self.config_manager = config_manager or ConfigurationManager()
        self.audio_engine = audio_engine or AudioEngine()
        self.event_bus = event_bus or EventBus()
        self.metrics = metrics or STTMetrics()
        self.diagnostics = diagnostics or STTDiagnostics(metrics=self.metrics)

        self._stt_config: STTConfiguration = self._load_stt_configuration()
        self.engine: ISTTEngine = engine or FasterWhisperSTTEngine(
            config=self._stt_config
        )
        self.speech_buffer = SpeechSegmentBuffer(
            sample_rate=16000,
            max_duration_seconds=round(
                self._stt_config.max_segment_duration_ms / 1000.0, 1
            ),
        )

        self._stt_state: STTState = STTState.DISABLED
        self._is_listening: bool = False
        self._callbacks: set[Callable[[TranscriptionResult], None]] = set()
        self._callbacks_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="FridaySTTWorker"
        )
        self._last_error: str | None = None

    @property
    def stt_config(self) -> STTConfiguration:
        """Active STT configuration model."""
        return self._stt_config

    @property
    def stt_state(self) -> STTState:
        """Current STT operational state."""
        return self._stt_state

    def _set_stt_state(self, new_state: STTState) -> None:
        """Transition STT state and publish EventBus notification."""
        if self._stt_state != new_state:
            prev = self._stt_state.value
            self._stt_state = new_state
            self.event_bus.publish(
                STTStateChanged(previous_state=prev, new_state=new_state.value)
            )

    def _load_stt_configuration(self) -> STTConfiguration:
        """Load STT configuration from ConfigurationManager."""
        try:
            settings = self.config_manager.settings
            if hasattr(settings, "stt"):
                stt_cfg = settings.stt
                return STTConfiguration(
                    enabled=stt_cfg.enabled,
                    model_name=stt_cfg.model_name,
                    device=stt_cfg.device,
                    compute_type=stt_cfg.compute_type,
                    language=stt_cfg.language,
                    beam_size=stt_cfg.beam_size,
                    max_segment_duration_ms=stt_cfg.max_segment_duration_ms,
                    word_timestamps=stt_cfg.word_timestamps,
                    vad_filter=stt_cfg.vad_filter,
                    custom_model_path=stt_cfg.custom_model_path,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"STTService: Failed to load STTSettings from config, using defaults: {exc}"
            )

        return STTConfiguration()

    def _do_initialize(self) -> None:
        """Initialize STT model."""
        if not self.stt_config.enabled:
            logger.info("STTService: Subsystem disabled in settings.")
            self._set_stt_state(STTState.DISABLED)
            return

        self._set_stt_state(STTState.LOADING)
        success = self.engine.load_model()
        if success:
            self._set_stt_state(STTState.READY)
            act_dev = getattr(self.engine, "actual_device", "cpu")
            act_comp = getattr(self.engine, "actual_compute_type", "int8")
            self.event_bus.publish(
                STTModelLoaded(
                    model_name=self.stt_config.model_name,
                    device=act_dev,
                    compute_type=act_comp,
                )
            )
            logger.info("STTService: Successfully initialized model.")
        else:
            self._set_stt_state(STTState.ERROR)
            self._last_error = "Failed to load STT model"
            self.event_bus.publish(STTError(error_message="Failed to load STT model"))
            logger.error("STTService: Initialization failed.")

    def _do_start(self) -> None:
        """Start listening for speech boundary events."""
        if self.stt_config.enabled:
            self.start_listening()

    def _do_stop(self) -> None:
        """Stop service, release model resources and shutdown background executor."""
        self.stop_listening()
        self.engine.unload_model()
        self._set_stt_state(STTState.UNLOADED)
        self.event_bus.publish(STTModelUnloaded())
        self._executor.shutdown(wait=False)
        logger.info("STTService: Stopped service.")

    def start_listening(self) -> None:
        """Subscribe to VAD speech boundary events and AudioEngine frames."""
        if self._is_listening:
            return

        self._is_listening = True
        self.event_bus.subscribe("SpeechStarted", self._on_speech_started)
        self.event_bus.subscribe("SpeechStopped", self._on_speech_stopped)
        self.audio_engine.subscribe(self._on_audio_frame)
        logger.info("STTService: Started listening for speech boundary events.")

    def stop_listening(self) -> None:
        """Unsubscribe from VAD speech boundary events and AudioEngine frames."""
        if not self._is_listening:
            return

        self._is_listening = False
        self.audio_engine.unsubscribe(self._on_audio_frame)
        self.event_bus.unsubscribe("SpeechStarted", self._on_speech_started)
        self.event_bus.unsubscribe("SpeechStopped", self._on_speech_stopped)
        self.speech_buffer.clear()
        logger.info("STTService: Stopped listening.")

    def _on_speech_started(self, event: Any) -> None:
        """EventBus handler when VAD confirms speech start."""
        if self._is_listening and self.stt_config.enabled:
            self.speech_buffer.start_collection()

    def _on_audio_frame(self, frame: AudioFrame) -> None:
        """AudioEngine subscriber receiving real-time audio frames."""
        if self._is_listening and self.speech_buffer.is_collecting:
            self.speech_buffer.push_frame(frame)

    def _on_speech_stopped(self, event: Any) -> None:
        """EventBus handler when VAD confirms speech stop."""
        if not self._is_listening or not self.stt_config.enabled:
            return

        audio_samples, duration_sec = self.speech_buffer.finalize()
        if duration_sec < 0.1 or len(audio_samples) == 0:
            logger.debug("STTService: Empty or short speech segment ignored.")
            return

        # Submit transcription job to background executor
        self._executor.submit(self._run_transcription_job, audio_samples, duration_sec)

    def _run_transcription_job(
        self, audio_samples: Any, audio_duration_sec: float
    ) -> None:
        """Background worker executing Faster-Whisper transcription."""
        if not self.engine.is_loaded:
            logger.warning("STTService: Transcription job skipped (model not loaded).")
            return

        prev_state = self._stt_state
        self._set_stt_state(STTState.TRANSCRIBING)

        self.event_bus.publish(
            TranscriptionStarted(
                audio_duration_seconds=audio_duration_sec,
                model_name=self.stt_config.model_name,
            )
        )

        try:
            result = self.engine.transcribe(audio_samples, sample_rate=16000)

            # Record metrics
            self.metrics.record_transcription(
                status=result.status,
                audio_duration_sec=result.duration_seconds,
                processing_time_sec=result.processing_time_seconds,
                text=result.text,
            )

            if result.status == "SUCCESS":
                self.event_bus.publish(
                    TranscriptionCompleted(
                        text=result.text,
                        language=result.language,
                        language_probability=result.language_probability,
                        audio_duration_seconds=result.duration_seconds,
                        processing_time_seconds=result.processing_time_seconds,
                        real_time_factor=result.real_time_factor,
                        model_name=result.model_name,
                        device=result.device,
                    )
                )
            elif result.status == "FAILED":
                err_msg = result.metadata.get("error", "Transcription failed")
                self.event_bus.publish(
                    TranscriptionFailed(
                        error_message=err_msg,
                        audio_duration_seconds=result.duration_seconds,
                    )
                )

            # Dispatch callbacks
            self._notify_callbacks(result)

        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
            self.metrics.record_error()
            self.event_bus.publish(
                TranscriptionFailed(
                    error_message=str(exc),
                    audio_duration_seconds=audio_duration_sec,
                )
            )
            logger.error(f"STTService: Transcription execution error: {exc}")
        finally:
            self._set_stt_state(STTState.READY if self.engine.is_loaded else prev_state)

    def transcribe_audio(
        self, audio_samples: Any, sample_rate: int = 16000
    ) -> TranscriptionResult:
        """Synchronously transcribe PCM float32 audio array."""
        return self.engine.transcribe(audio_samples, sample_rate=sample_rate)

    def register_callback(
        self, callback: Callable[[TranscriptionResult], None]
    ) -> None:
        """Register callback for transcription events."""
        with self._callbacks_lock:
            self._callbacks.add(callback)

    def unregister_callback(
        self, callback: Callable[[TranscriptionResult], None]
    ) -> None:
        """Unregister callback."""
        with self._callbacks_lock:
            self._callbacks.discard(callback)

    def _notify_callbacks(self, result: TranscriptionResult) -> None:
        """Invoke all registered callbacks."""
        with self._callbacks_lock:
            cbs = list(self._callbacks)

        for cb in cbs:
            try:
                cb(result)
            except Exception as exc:  # noqa: BLE001
                logger.error(f"STTService: Callback execution exception: {exc}")

    def get_health_report(self) -> dict[str, Any]:
        """Generate diagnostic health report."""
        act_dev = getattr(self.engine, "actual_device", "cpu")
        act_comp = getattr(self.engine, "actual_compute_type", "int8")

        return self.diagnostics.get_health_report(
            service_state=self.stt_state.value,
            model_name=self.stt_config.model_name,
            model_loaded=self.engine.is_loaded,
            device=act_dev,
            compute_type=act_comp,
            listening=self._is_listening,
            enabled=self.stt_config.enabled,
            language=self.stt_config.language,
            last_error=self._last_error,
        )

    def health_check(self) -> dict[str, Any]:
        """HealthMonitor service integration hook."""
        base = super().health_check()
        base.update(self.get_health_report())
        return base
