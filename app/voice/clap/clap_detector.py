"""Concrete ClapDetector service subscribing to AudioEngine frames and publishing activation events."""

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
from app.voice.clap.clap_detector_interface import IClapDetector
from app.voice.clap.diagnostics import ClapDiagnostics
from app.voice.clap.events import (
    ClapDetected,
    ClapDetectionError,
    ClapDetectionStarted,
    ClapDetectionStopped,
    DoubleClapDetected,
)
from app.voice.clap.metrics import ClapMetrics
from app.voice.clap.models import ClapConfiguration, ClapEvent, ClapState
from app.voice.clap.signal_processor import ClapSignalProcessor
from app.voice.clap.state_machine import DoubleClapStateMachine


class ClapDetector(BaseService, IClapDetector):
    """Central Clap Detection Subsystem service managing frame processing, state machine, and event publishing.

    Architecture Guarantee:
    - Reuses Phase 3.1 AudioEngine frame subscription (zero duplicate sounddevice pipelines).
    - Local, deterministic transient signal analysis (zero LLMs, zero cloud calls).
    - Emits DoubleClapDetected via EventBus strictly when gesture matches timing window.
    """

    def __init__(
        self,
        config_manager: ConfigurationManager | None = None,
        audio_engine: AudioEngine | None = None,
        event_bus: EventBus | None = None,
        metrics: ClapMetrics | None = None,
        diagnostics: ClapDiagnostics | None = None,
    ) -> None:
        super().__init__(name="ClapDetector", is_critical=False)
        self.config_manager = config_manager or ConfigurationManager()
        self.audio_engine = audio_engine
        self.event_bus = event_bus or EventBus()
        self.metrics = metrics or ClapMetrics()
        self.diagnostics = diagnostics or ClapDiagnostics(metrics=self.metrics)

        self.config: ClapConfiguration = self._load_configuration()
        self.signal_processor = ClapSignalProcessor(config=self.config)
        self.state_machine = DoubleClapStateMachine(
            config=self.config, metrics=self.metrics
        )

        self._is_listening: bool = False
        self._last_clap_timestamp: float | None = None
        self._last_error: str | None = None
        self._activation_listeners: list[Callable[[DoubleClapDetected], None]] = []
        self._lock = threading.Lock()

    @property
    def state(self) -> ClapState:
        """Current state of double clap state machine."""
        return self.state_machine.state

    @property
    def is_listening(self) -> bool:
        """True if ClapDetector is actively consuming AudioFrames."""
        with self._lock:
            return self._is_listening

    def _load_configuration(self) -> ClapConfiguration:
        """Load ClapConfiguration from Settings Manager."""
        settings: Settings = self.config_manager.settings
        clap_cfg = settings.clap

        return ClapConfiguration(
            enabled=clap_cfg.enabled,
            min_clap_interval_ms=clap_cfg.min_clap_interval_ms,
            max_clap_interval_ms=clap_cfg.max_clap_interval_ms,
            cooldown_ms=clap_cfg.cooldown_ms,
            energy_threshold_multiplier=clap_cfg.energy_threshold_multiplier,
            min_peak_amplitude=clap_cfg.min_peak_amplitude,
            min_duration_ms=clap_cfg.min_duration_ms,
            max_duration_ms=clap_cfg.max_duration_ms,
            confidence_threshold=clap_cfg.confidence_threshold,
        )

    def _do_initialize(self) -> None:
        """Lifecycle Hook 1: Initialize signal processor & state machine parameters."""
        logger.info("ClapDetector: Initialized service parameters.")

    def _do_start(self) -> None:
        """Lifecycle Hook 2: Start listening for audio frames if enabled."""
        if self.config.enabled:
            self.start_listening()

    def _do_stop(self) -> None:
        """Lifecycle Hook 3: Stop listening for audio frames."""
        self.stop_listening()

    def start_listening(self) -> None:
        """Subscribe to AudioEngine frame stream and begin clap gesture detection."""
        with self._lock:
            if self._is_listening:
                return

            self._is_listening = True

        if self.audio_engine:
            self.audio_engine.subscribe(self._on_audio_frame)

        self.event_bus.publish(ClapDetectionStarted())
        logger.info("ClapDetector: Started listening for double claps.")

    def stop_listening(self) -> None:
        """Unsubscribe from AudioEngine frame stream and stop clap gesture detection."""
        with self._lock:
            if not self._is_listening:
                return

            self._is_listening = False

        if self.audio_engine:
            self.audio_engine.unsubscribe(self._on_audio_frame)

        self.event_bus.publish(ClapDetectionStopped())
        logger.info("ClapDetector: Stopped listening.")

    def reset(self) -> None:
        """Reset state machine, signal processor baseline, and error states."""
        self.signal_processor.reset()
        self.state_machine.reset()
        with self._lock:
            self._last_error = None
            self._last_clap_timestamp = None
        logger.info("ClapDetector: Reset state machine and signal processor.")

    def subscribe_activation(
        self, callback: Callable[[DoubleClapDetected], None]
    ) -> None:
        """Subscribe a callback listener to DoubleClapDetected activation events."""
        with self._lock:
            if callback not in self._activation_listeners:
                self._activation_listeners.append(callback)

    def unsubscribe_activation(
        self, callback: Callable[[DoubleClapDetected], None]
    ) -> None:
        """Unsubscribe an activation listener callback."""
        with self._lock:
            if callback in self._activation_listeners:
                self._activation_listeners.remove(callback)

    def process_frame(self, frame: AudioFrame) -> ClapEvent | None:
        """Process an AudioFrame and evaluate for double clap activation.

        Returns:
            ClapEvent | None: Evaluated ClapEvent if a valid clap impulse was detected.
        """
        start_time = time.perf_counter()
        self.metrics.record_frame_analyzed()

        try:
            clap_event = self.signal_processor.process_frame(frame)
            if not clap_event:
                return None

            # Record metrics for candidate transient
            self.metrics.record_candidate()
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            self.metrics.record_valid_clap(
                confidence=clap_event.confidence, latency_ms=latency_ms
            )

            with self._lock:
                self._last_clap_timestamp = clap_event.timestamp

            # Publish single ClapDetected event
            self.event_bus.publish(
                ClapDetected(
                    timestamp=clap_event.timestamp,
                    confidence=clap_event.confidence,
                    peak_amplitude=clap_event.peak_amplitude,
                    energy=clap_event.energy,
                )
            )

            # Evaluate state machine for Double Clap gesture
            is_activated, interval_ms = self.state_machine.process_clap_event(
                clap_event
            )

            if is_activated:
                first_ts = (
                    self.state_machine.first_clap_timestamp or clap_event.timestamp
                )
                act_event = DoubleClapDetected(
                    first_clap_timestamp=first_ts,
                    second_clap_timestamp=clap_event.timestamp,
                    interval_ms=interval_ms,
                    confidence=clap_event.confidence,
                )

                # 1. Publish to EventBus
                self.event_bus.publish(act_event)

                # 2. Dispatch to local activation listeners
                with self._lock:
                    listeners_copy = list(self._activation_listeners)

                for listener in listeners_copy:
                    try:
                        listener(act_event)
                    except Exception as exc:  # noqa: BLE001
                        logger.error(
                            f"ClapDetector: Activation listener exception: {exc}"
                        )

            return clap_event
        except Exception as exc:  # noqa: BLE001
            self.metrics.record_error()
            with self._lock:
                self._last_error = str(exc)
            self.event_bus.publish(
                ClapDetectionError(
                    error_code="FRAME_PROCESSING_ERROR",
                    message="Error processing audio frame for clap detection",
                    details=str(exc),
                )
            )
            logger.error(f"ClapDetector: Error processing frame: {exc}")
            return None

    def _on_audio_frame(self, frame: AudioFrame) -> None:
        """AudioEngine subscription callback invoked for each real-time AudioFrame."""
        if not self.is_listening:
            return
        self.process_frame(frame)

    def get_configuration(self) -> ClapConfiguration:
        """Get active clap configuration model."""
        return self.config

    def get_health_report(self) -> dict[str, Any]:
        """Generate diagnostic health report."""
        return self.diagnostics.get_health_report(
            detector_state=self.state,
            enabled=self.config.enabled,
            config=self.config,
            noise_floor_energy=self.signal_processor.noise_floor,
            last_clap_timestamp=self._last_clap_timestamp,
            last_error=self._last_error,
        )

    def health_check(self) -> dict[str, Any]:
        """HealthMonitor service integration hook."""
        base = super().health_check()
        base.update(self.get_health_report())
        return base
