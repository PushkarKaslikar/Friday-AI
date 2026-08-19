"""Voice Activity Detector service.

Phase 3.4 - Voice Activity Detection & Speech Boundary Engine
"""

import time
from collections.abc import Callable
from typing import Any

from app.config.manager import ConfigurationManager
from app.logging import logger
from app.services.base.service_interface import BaseService
from app.services.events.event_bus import EventBus
from app.voice.audio.audio_engine import AudioEngine
from app.voice.audio.models import AudioFrame
from app.voice.vad.audio_adapter import VADAudioAdapter
from app.voice.vad.diagnostics import VADDiagnostics
from app.voice.vad.events import (
    SpeechStarted,
    SpeechStopped,
    VADDetectorStarted,
    VADDetectorStopped,
    VADError,
    VADModelLoaded,
    VADModelUnloaded,
    VADStateChanged,
)
from app.voice.vad.metrics import VADMetrics
from app.voice.vad.models import SpeechSegment, VADConfiguration, VADState
from app.voice.vad.silero_vad_model import SileroVADModel
from app.voice.vad.state_machine import VADStateMachine
from app.voice.vad.vad_detector_interface import IVADDetector
from app.voice.vad.vad_model_interface import IVADModel


class VADDetector(BaseService, IVADDetector):
    """Local Voice Activity Detection service backed by Silero VAD ONNX model."""

    def __init__(
        self,
        config_manager: ConfigurationManager,
        audio_engine: AudioEngine,
        event_bus: EventBus,
        model: IVADModel | None = None,
        metrics: VADMetrics | None = None,
        diagnostics: VADDiagnostics | None = None,
    ) -> None:
        super().__init__("VADDetector")
        self.config_manager = config_manager
        self.audio_engine = audio_engine
        self.event_bus = event_bus

        # Read configuration settings
        self.vad_config = self._load_vad_configuration()

        # Components
        self.model = model or SileroVADModel(config=self.vad_config)
        self.metrics = metrics or VADMetrics()
        self.diagnostics = diagnostics or VADDiagnostics(
            config=self.vad_config, metrics=self.metrics
        )

        # State machine
        self.state_machine = VADStateMachine(
            config=self.vad_config,
            on_speech_started=self._handle_speech_started,
            on_speech_stopped=self._handle_speech_stopped,
            on_state_changed=self._handle_state_changed,
        )

        self._is_listening: bool = False
        self._active_segment: SpeechSegment | None = None
        self._started_callbacks: list[Callable[[float, float], None]] = []
        self._stopped_callbacks: list[Callable[[SpeechSegment], None]] = []

    def _load_vad_configuration(self) -> VADConfiguration:
        """Extract VADConfiguration from SettingsManager."""
        try:
            settings = getattr(self.config_manager, "settings", None) or (
                self.config_manager.get_settings()
                if hasattr(self.config_manager, "get_settings")
                else None
            )
            vad_s = getattr(settings, "voice", None)
            if vad_s and hasattr(vad_s, "vad"):
                v = vad_s.vad
                return VADConfiguration(
                    enabled=v.enabled,
                    model_name=v.model_name,
                    custom_model_path=v.custom_model_path,
                    speech_threshold=v.speech_threshold,
                    negative_threshold=v.negative_threshold,
                    speech_start_confirmation_ms=v.speech_start_confirmation_ms,
                    min_silence_duration_ms=v.min_silence_duration_ms,
                    speech_pad_ms=v.speech_pad_ms,
                    sample_rate=v.sample_rate,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"VADDetector: Failed to load VADSettings from config, using defaults: {exc}"
            )
        return VADConfiguration()

    @property
    def vad_state(self) -> VADState:
        """Get current operational/speech tracking state."""
        return self.state_machine.current_state

    @property
    def is_listening(self) -> bool:
        """Check if detector is actively receiving audio frames."""
        return self._is_listening

    def _do_initialize(self) -> None:
        """Initialize Silero VAD model session."""
        if not self.vad_config.enabled:
            logger.info("VADDetector: Disabled in settings.")
            return

        success = self.model.load_model()
        if success:
            model_path = getattr(self.model, "model_path", self.vad_config.model_name)
            self.event_bus.publish(
                VADModelLoaded(
                    model_name=self.vad_config.model_name, model_path=model_path
                )
            )
            logger.info("VADDetector: Successfully initialized model.")
        else:
            self.event_bus.publish(
                VADError(error_message="Failed to load Silero VAD model.")
            )
            logger.error("VADDetector: Failed to initialize Silero VAD model.")

    def _do_start(self) -> None:
        """Start listening for audio frames."""
        if not self.vad_config.enabled:
            logger.info("VADDetector: Cannot start, disabled in settings.")
            return

        if not self.model.is_loaded:
            logger.warning("VADDetector: Model not loaded, attempting load...")
            if not self.model.load_model():
                logger.error("VADDetector: Cannot start, model load failed.")
                return

        self.start_listening()

    def _do_stop(self) -> None:
        """Stop listening and unload model."""
        self.stop_listening()
        self.model.unload_model()
        self.event_bus.publish(VADModelUnloaded())
        logger.info("VADDetector: Stopped service.")

    def start_listening(self) -> bool:
        """Subscribe to AudioEngine frame delivery."""
        if self._is_listening:
            return True

        self.audio_engine.subscribe(self._on_audio_frame)
        self._is_listening = True
        self.state_machine.reset()
        self.event_bus.publish(
            VADDetectorStarted(
                model_name=self.vad_config.model_name,
                sample_rate=self.vad_config.sample_rate,
                threshold=self.vad_config.speech_threshold,
            )
        )
        logger.info("VADDetector: Started listening for voice activity.")
        return True

    def stop_listening(self) -> None:
        """Unsubscribe from AudioEngine frame delivery."""
        if not self._is_listening:
            return

        self.audio_engine.unsubscribe(self._on_audio_frame)
        self._is_listening = False
        self.state_machine.reset()
        self._active_segment = None
        self.event_bus.publish(VADDetectorStopped())
        logger.info("VADDetector: Stopped listening for voice activity.")

    def add_speech_callback(
        self,
        on_started: Callable[[float, float], None] | None = None,
        on_stopped: Callable[[SpeechSegment], None] | None = None,
    ) -> None:
        """Register callbacks for speech boundary events."""
        if on_started:
            self._started_callbacks.append(on_started)
        if on_stopped:
            self._stopped_callbacks.append(on_stopped)

    def _on_audio_frame(self, frame: AudioFrame) -> None:
        """Real-time callback receiving audio frames from AudioEngine."""
        if not self._is_listening or not self.model.is_loaded:
            return

        t_start = time.perf_counter()
        try:
            samples = VADAudioAdapter.prepare_samples(frame)
            probability = self.model.process_audio(samples)
            latency_ms = (time.perf_counter() - t_start) * 1000.0

            # Record frame statistics
            self.metrics.record_frame(probability, latency_ms)

            # Update active segment statistics if speaking
            if self._active_segment is not None:
                self._active_segment.update_frame(probability)

            # Feed probability into state machine
            frame_dur_ms = getattr(frame, "duration_ms", frame.duration * 1000.0)
            self.state_machine.process_frame(
                probability=probability,
                frame_duration_ms=frame_dur_ms,
                timestamp=frame.timestamp,
            )
        except Exception as exc:  # noqa: BLE001
            self.metrics.record_error()
            logger.error(f"VADDetector: Frame processing error: {exc}")
            self.event_bus.publish(
                VADError(error_message=f"Frame processing error: {exc}")
            )

    def _handle_speech_started(self, probability: float, timestamp: float) -> None:
        """Handle confirmed SpeechStarted state transition."""
        self._active_segment = SpeechSegment(
            start_timestamp=timestamp,
            peak_probability=probability,
            average_probability=probability,
            frame_count=1,
        )
        self.metrics.record_speech_started()

        event = SpeechStarted(
            speech_probability=probability,
            threshold=self.vad_config.speech_threshold,
            audio_timestamp=timestamp,
        )
        self.event_bus.publish(event)
        logger.info(
            f"VADDetector: SpeechStarted detected (prob: {probability:.2f}, threshold: {self.vad_config.speech_threshold})."
        )

        for callback in self._started_callbacks:
            try:
                callback(probability, timestamp)
            except Exception as exc:  # noqa: BLE001
                logger.error(f"VADDetector: SpeechStarted callback exception: {exc}")

    def _handle_speech_stopped(
        self, speech_duration: float, final_probability: float, silence_duration: float
    ) -> None:
        """Handle confirmed SpeechStopped state transition."""
        now = time.time()
        start_ts = (
            self._active_segment.start_timestamp
            if self._active_segment
            else now - speech_duration
        )

        segment = self._active_segment or SpeechSegment(start_timestamp=start_ts)
        segment.finalize(now)
        self._active_segment = None

        self.metrics.record_speech_stopped(
            duration_seconds=speech_duration, silence_seconds=silence_duration
        )

        event = SpeechStopped(
            speech_duration=round(speech_duration, 3),
            final_probability=round(final_probability, 3),
            silence_duration=round(silence_duration, 3),
            audio_start_timestamp=start_ts,
            audio_end_timestamp=now,
        )
        self.event_bus.publish(event)
        logger.info(
            f"VADDetector: SpeechStopped detected (duration: {speech_duration:.2f}s, silence: {silence_duration:.2f}s)."
        )

        for callback in self._stopped_callbacks:
            try:
                callback(segment)
            except Exception as exc:  # noqa: BLE001
                logger.error(f"VADDetector: SpeechStopped callback exception: {exc}")

    def _handle_state_changed(self, old_state: VADState, new_state: VADState) -> None:
        """Publish VADStateChanged event on state machine transition."""
        self.event_bus.publish(
            VADStateChanged(previous_state=old_state.value, new_state=new_state.value)
        )
        if new_state == VADState.IDLE and old_state == VADState.SPEECH_CANDIDATE:
            self.metrics.record_false_start()
        elif new_state == VADState.SILENCE_CANDIDATE:
            self.metrics.record_silence_candidate()

    def get_health_report(self) -> dict[str, Any]:
        """Generate diagnostic health report."""
        model_path = getattr(self.model, "model_path", self.vad_config.model_name)
        return self.diagnostics.generate_health_report(
            current_state=self.vad_state,
            is_model_loaded=self.model.is_loaded,
            is_listening=self._is_listening,
            model_path=model_path,
        )
