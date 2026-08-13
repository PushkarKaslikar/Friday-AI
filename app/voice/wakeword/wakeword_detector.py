"""Concrete WakeWordDetector service running OpenWakeWord ONNX inference and publishing activation events."""

import threading
import time
from collections.abc import Callable
from typing import Any

from app.config.manager import ConfigurationManager
from app.config.models import Settings
from app.logging import logger
from app.services.base.service_interface import BaseService
from app.services.events.event_bus import EventBus
from app.voice.audio.audio_engine import AudioEngine
from app.voice.audio.models import AudioFrame
from app.voice.wakeword.audio_adapter import WakeWordAudioAdapter
from app.voice.wakeword.diagnostics import WakeWordDiagnostics
from app.voice.wakeword.events import (
    WakeWordDetected,
    WakeWordDetectionError,
    WakeWordDetectorStarted,
    WakeWordDetectorStopped,
    WakeWordModelLoaded,
    WakeWordModelUnloaded,
)
from app.voice.wakeword.metrics import WakeWordMetrics
from app.voice.wakeword.model_provider import WakeWordModelProvider
from app.voice.wakeword.models import (
    WakeWordConfiguration,
    WakeWordEvent,
    WakeWordState,
)
from app.voice.wakeword.wakeword_detector_interface import IWakeWordDetector


class WakeWordDetector(BaseService, IWakeWordDetector):
    """Central Wake Word Subsystem service managing ONNX model inference, thresholding, and event publishing.

    Architecture Guarantee:
    - Reuses Phase 3.1 AudioEngine frame subscription (zero duplicate sounddevice pipelines).
    - Alternative, independent activation mechanism alongside Phase 3.2 Double Clap.
    - 100% local OpenWakeWord ONNX inference (zero cloud APIs, zero audio persistence).
    """

    def __init__(
        self,
        config_manager: ConfigurationManager | None = None,
        audio_engine: AudioEngine | None = None,
        event_bus: EventBus | None = None,
        model_provider: WakeWordModelProvider | None = None,
        metrics: WakeWordMetrics | None = None,
        diagnostics: WakeWordDiagnostics | None = None,
    ) -> None:
        super().__init__(name="WakeWordDetector", is_critical=False)
        self.config_manager = config_manager or ConfigurationManager()
        self.audio_engine = audio_engine
        self.event_bus = event_bus or EventBus()
        self.metrics = metrics or WakeWordMetrics()
        self.diagnostics = diagnostics or WakeWordDiagnostics(metrics=self.metrics)

        self.config: WakeWordConfiguration = self._load_configuration()
        self.model_provider = model_provider or WakeWordModelProvider(
            config=self.config
        )
        self.audio_adapter = WakeWordAudioAdapter()

        self._detector_state: WakeWordState = WakeWordState.DISABLED
        self._is_listening: bool = False
        self._cooldown_until: float = 0.0
        self._last_detection_timestamp: float | None = None
        self._last_error: str | None = None
        self._activation_listeners: list[Callable[[WakeWordDetected], None]] = []
        self._lock = threading.Lock()

    @property
    def detector_state(self) -> WakeWordState:
        """Current state of WakeWordDetector service."""
        with self._lock:
            return self._detector_state

    @property
    def is_listening(self) -> bool:
        """True if WakeWordDetector is actively processing AudioFrames."""
        with self._lock:
            return self._is_listening

    def _load_configuration(self) -> WakeWordConfiguration:
        """Load WakeWordConfiguration from Settings Manager."""
        settings: Settings = self.config_manager.settings
        ww_cfg = settings.wake_word

        return WakeWordConfiguration(
            enabled=ww_cfg.enabled,
            model_name=ww_cfg.model_name,
            custom_model_path=ww_cfg.custom_model_path,
            threshold=ww_cfg.threshold,
            cooldown_ms=ww_cfg.cooldown_ms,
        )

    def _do_initialize(self) -> None:
        """Lifecycle Hook 1: Load OpenWakeWord model."""
        with self._lock:
            self._detector_state = WakeWordState.LOADING

        success = self.model_provider.load_model()
        with self._lock:
            if success:
                self._detector_state = WakeWordState.READY
                self.event_bus.publish(
                    WakeWordModelLoaded(
                        model_id=self.model_provider.active_model_name,
                        model_path=self.model_provider.model_path,
                    )
                )
                logger.info("WakeWordDetector: Successfully initialized model.")
            else:
                self._detector_state = WakeWordState.ERROR
                self._last_error = "Failed to load OpenWakeWord model"
                self.event_bus.publish(
                    WakeWordDetectionError(
                        error_code="MODEL_LOAD_FAILED",
                        message="OpenWakeWord model loading failed",
                    )
                )
                logger.error("WakeWordDetector: Model initialization failed.")

    def _do_start(self) -> None:
        """Lifecycle Hook 2: Start listening if enabled and ready."""
        if self.config.enabled:
            self.start_listening()

    def _do_stop(self) -> None:
        """Lifecycle Hook 3: Stop listening and unload model resources."""
        self.stop_listening()
        self.model_provider.unload_model()
        with self._lock:
            self._detector_state = WakeWordState.DISABLED
        self.event_bus.publish(WakeWordModelUnloaded(model_id=self.config.model_name))

    def start_listening(self) -> None:
        """Subscribe to AudioEngine frame stream and begin wake word inference."""
        with self._lock:
            if self._is_listening:
                return

            if not self.model_provider.is_loaded:
                logger.warning(
                    "WakeWordDetector: Cannot start listening; model is not loaded."
                )
                return

            self._is_listening = True
            self._detector_state = WakeWordState.LISTENING

        if self.audio_engine:
            self.audio_engine.subscribe(self._on_audio_frame)

        self.event_bus.publish(
            WakeWordDetectorStarted(model_id=self.model_provider.active_model_name)
        )
        logger.info("WakeWordDetector: Started listening for wake word.")

    def stop_listening(self) -> None:
        """Unsubscribe from AudioEngine frame stream and stop wake word inference."""
        with self._lock:
            if not self._is_listening:
                return

            self._is_listening = False
            if self._detector_state == WakeWordState.LISTENING:
                self._detector_state = WakeWordState.READY

        if self.audio_engine:
            self.audio_engine.unsubscribe(self._on_audio_frame)

        self.event_bus.publish(WakeWordDetectorStopped())
        logger.info("WakeWordDetector: Stopped listening.")

    def reset(self) -> None:
        """Reset refractory cooldown and error states."""
        with self._lock:
            self._cooldown_until = 0.0
            self._last_error = None
            self._last_detection_timestamp = None
            if self.model_provider.is_loaded:
                self._detector_state = (
                    WakeWordState.LISTENING
                    if self._is_listening
                    else WakeWordState.READY
                )
        logger.info("WakeWordDetector: Reset state parameters.")

    def subscribe_activation(
        self, callback: Callable[[WakeWordDetected], None]
    ) -> None:
        """Subscribe a listener callback to WakeWordDetected activation events."""
        with self._lock:
            if callback not in self._activation_listeners:
                self._activation_listeners.append(callback)

    def unsubscribe_activation(
        self, callback: Callable[[WakeWordDetected], None]
    ) -> None:
        """Unsubscribe an activation listener callback."""
        with self._lock:
            if callback in self._activation_listeners:
                self._activation_listeners.remove(callback)

    def process_frame(self, frame: AudioFrame) -> WakeWordEvent | None:
        """Process an AudioFrame for wake word ONNX inference.

        Returns:
            WakeWordEvent | None: Evaluated WakeWordEvent if wake word score >= threshold.
        """
        self.metrics.record_frame_analyzed()

        start_time = time.perf_counter()
        now = frame.timestamp

        with self._lock:
            # 1. Refractory Cooldown Check
            if now < self._cooldown_until:
                self.metrics.record_cooldown_suppression()
                return None

        # 2. Convert AudioFrame to int16 PCM array
        int16_samples = self.audio_adapter.adapt_frame(frame)
        if len(int16_samples) == 0:
            return None

        # 3. Perform ONNX Inference
        predictions = self.model_provider.predict(int16_samples)
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        self.metrics.record_inference(latency_ms)

        if not predictions:
            return None

        # 4. Extract max score matching model
        max_score = 0.0
        detected_key = self.model_provider.active_model_name
        for key, val in predictions.items():
            score_val = float(val)
            if score_val > max_score:
                max_score = score_val
                detected_key = key

        # 5. Threshold Evaluation
        if max_score < self.config.threshold:
            self.metrics.record_rejected_prediction()
            return None

        # 6. Valid Wake Word Detected!
        self.metrics.record_detection(max_score)

        with self._lock:
            self._cooldown_until = now + (self.config.cooldown_ms / 1000.0)
            self._last_detection_timestamp = now
            self._detector_state = WakeWordState.DETECTED

        event = WakeWordEvent(
            timestamp=now,
            wake_word=detected_key,
            score=round(max_score, 3),
            threshold=self.config.threshold,
            model_id=self.model_provider.active_model_name,
            signal_quality="HIGH" if max_score >= 0.85 else "MEDIUM",
        )

        act_event = WakeWordDetected(
            wake_word=detected_key,
            score=round(max_score, 3),
            threshold=self.config.threshold,
            timestamp=now,
            model_id=self.model_provider.active_model_name,
        )

        logger.info(
            f"WakeWordDetector: WAKE WORD DETECTED! '{detected_key}' (score: {max_score:.2f} >= {self.config.threshold})."
        )

        # Publish to EventBus
        self.event_bus.publish(act_event)

        # Dispatch to local activation listeners
        with self._lock:
            listeners_copy = list(self._activation_listeners)

        for listener in listeners_copy:
            try:
                listener(act_event)
            except Exception as exc:  # noqa: BLE001
                logger.error(f"WakeWordDetector: Listener exception: {exc}")

        return event

    def _on_audio_frame(self, frame: AudioFrame) -> None:
        """AudioEngine subscription callback invoked for each real-time AudioFrame."""
        if not self.is_listening:
            return
        self.process_frame(frame)

    def get_configuration(self) -> WakeWordConfiguration:
        """Get active wake word configuration model."""
        return self.config

    def get_health_report(self) -> dict[str, Any]:
        """Generate diagnostic health report."""
        return self.diagnostics.get_health_report(
            detector_state=self.detector_state,
            enabled=self.config.enabled,
            config=self.config,
            active_model_name=self.model_provider.active_model_name,
            model_path=self.model_provider.model_path,
            is_model_loaded=self.model_provider.is_loaded,
            is_custom_friday_model=self.model_provider.is_custom_friday_model,
            last_detection_timestamp=self._last_detection_timestamp,
            last_error=self._last_error,
        )

    def health_check(self) -> dict[str, Any]:
        """HealthMonitor service integration hook."""
        base = super().health_check()
        base.update(self.get_health_report())
        return base
