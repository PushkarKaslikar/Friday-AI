"""Deterministic Voice Activity Detection state machine.

Phase 3.4 - Voice Activity Detection & Speech Boundary Engine
"""

from collections.abc import Callable

from loguru import logger

from app.voice.vad.models import VADConfiguration, VADState


class VADStateMachine:
    """State machine tracking speech activity transitions and boundary events."""

    def __init__(
        self,
        config: VADConfiguration | None = None,
        on_speech_started: Callable[[float, float], None] | None = None,
        on_speech_stopped: Callable[[float, float, float], None] | None = None,
        on_state_changed: Callable[[VADState, VADState], None] | None = None,
    ) -> None:
        self.config = config or VADConfiguration()
        self.on_speech_started = on_speech_started
        self.on_speech_stopped = on_speech_stopped
        self.on_state_changed = on_state_changed

        self._state: VADState = VADState.IDLE
        self._candidate_duration_ms: float = 0.0
        self._silence_duration_ms: float = 0.0
        self._speech_start_timestamp: float = 0.0
        self._last_speech_probability: float = 0.0

    @property
    def current_state(self) -> VADState:
        """Get current VAD state machine state."""
        return self._state

    def reset(self) -> None:
        """Reset state machine to IDLE."""
        self._transition_to(VADState.IDLE)
        self._candidate_duration_ms = 0.0
        self._silence_duration_ms = 0.0
        self._speech_start_timestamp = 0.0
        self._last_speech_probability = 0.0

    def _transition_to(self, new_state: VADState) -> None:
        """Internal helper to update state and emit change notification."""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            logger.debug(
                f"VADStateMachine: State transition {old_state.value} -> {new_state.value}"
            )
            if self.on_state_changed:
                try:
                    self.on_state_changed(old_state, new_state)
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        f"VADStateMachine: State change callback exception: {exc}"
                    )

    def process_frame(
        self,
        probability: float,
        frame_duration_ms: float = 32.0,
        timestamp: float = 0.0,
    ) -> VADState:
        """Process frame speech probability and trigger state transitions.

        Args:
            probability: Silero speech probability (0.0 to 1.0)
            frame_duration_ms: Frame duration in milliseconds (default: 32.0)
            timestamp: Frame timestamp

        Returns:
            VADState: Updated state machine state
        """
        self._last_speech_probability = probability

        if self._state == VADState.IDLE:
            if probability >= self.config.speech_threshold:
                self._candidate_duration_ms = frame_duration_ms
                self._transition_to(VADState.SPEECH_CANDIDATE)
                if (
                    self._candidate_duration_ms
                    >= self.config.speech_start_confirmation_ms
                ):
                    self._speech_start_timestamp = timestamp
                    self._transition_to(VADState.SPEAKING)
                    if self.on_speech_started:
                        self.on_speech_started(probability, timestamp)

        elif self._state == VADState.SPEECH_CANDIDATE:
            if probability >= self.config.speech_threshold:
                self._candidate_duration_ms += frame_duration_ms
                if (
                    self._candidate_duration_ms
                    >= self.config.speech_start_confirmation_ms
                ):
                    self._speech_start_timestamp = timestamp
                    self._transition_to(VADState.SPEAKING)
                    if self.on_speech_started:
                        self.on_speech_started(probability, timestamp)
            elif probability < self.config.negative_threshold:
                # False start candidate rejection
                self._candidate_duration_ms = 0.0
                self._transition_to(VADState.IDLE)

        elif self._state == VADState.SPEAKING:
            if probability < self.config.negative_threshold:
                self._silence_duration_ms = frame_duration_ms
                self._transition_to(VADState.SILENCE_CANDIDATE)
                if self._silence_duration_ms >= self.config.min_silence_duration_ms:
                    speech_dur = (
                        timestamp - self._speech_start_timestamp
                        if timestamp > self._speech_start_timestamp
                        else 0.0
                    )
                    silence_dur_sec = self._silence_duration_ms / 1000.0
                    self._transition_to(VADState.IDLE)
                    if self.on_speech_stopped:
                        self.on_speech_stopped(speech_dur, probability, silence_dur_sec)

        elif self._state == VADState.SILENCE_CANDIDATE:
            if probability >= self.config.speech_threshold:
                # Speech resumed during pause
                self._silence_duration_ms = 0.0
                self._transition_to(VADState.SPEAKING)
            else:
                self._silence_duration_ms += frame_duration_ms
                if self._silence_duration_ms >= self.config.min_silence_duration_ms:
                    speech_dur = (
                        timestamp - self._speech_start_timestamp
                        if timestamp > self._speech_start_timestamp
                        else 0.0
                    )
                    silence_dur_sec = self._silence_duration_ms / 1000.0
                    self._transition_to(VADState.IDLE)
                    if self.on_speech_stopped:
                        self.on_speech_stopped(speech_dur, probability, silence_dur_sec)

        return self._state
