"""Operational performance metrics for Conversation State Machine.

Phase 3.7 - Conversation State Machine & Real-Time Voice Orchestration
"""

import threading
from typing import Any

import numpy as np

from app.voice.conversation.models import ActivationSource


class ConversationMetrics:
    """Thread-safe collector for conversation state machine metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._activations_total: int = 0
        self._double_clap_activations: int = 0
        self._wake_word_activations: int = 0
        self._manual_activations: int = 0
        self._sessions_started: int = 0
        self._sessions_completed: int = 0
        self._sessions_timed_out: int = 0
        self._speech_turns: int = 0
        self._barge_ins: int = 0
        self._state_transition_count: int = 0
        self._invalid_transition_count: int = 0
        self._stt_failures: int = 0
        self._tts_failures: int = 0
        self._errors_count: int = 0
        self._session_durations_sec: list[float] = []

    def record_activation(self, source: ActivationSource) -> None:
        """Record activation trigger event."""
        with self._lock:
            self._activations_total += 1
            self._sessions_started += 1
            if source == ActivationSource.DOUBLE_CLAP:
                self._double_clap_activations += 1
            elif source == ActivationSource.WAKE_WORD:
                self._wake_word_activations += 1
            else:
                self._manual_activations += 1

    def record_state_transition(self, is_valid: bool = True) -> None:
        """Record state machine transition."""
        with self._lock:
            self._state_transition_count += 1
            if not is_valid:
                self._invalid_transition_count += 1

    def record_turn(self) -> None:
        """Record completed conversational turn."""
        with self._lock:
            self._speech_turns += 1

    def record_barge_in(self) -> None:
        """Record user barge-in interruption."""
        with self._lock:
            self._barge_ins += 1

    def record_session_end(self, reason: str, duration_sec: float) -> None:
        """Record session termination."""
        with self._lock:
            if reason == "session_timeout":
                self._sessions_timed_out += 1
            else:
                self._sessions_completed += 1

            self._session_durations_sec.append(duration_sec)
            if len(self._session_durations_sec) > 1000:
                self._session_durations_sec.pop(0)

    def record_error(self, error_type: str = "general") -> None:
        """Record error."""
        with self._lock:
            self._errors_count += 1
            if error_type == "stt":
                self._stt_failures += 1
            elif error_type == "tts":
                self._tts_failures += 1

    def get_metrics_snapshot(self) -> dict[str, Any]:
        """Return thread-safe snapshot of collected conversation metrics."""
        with self._lock:
            avg_duration = (
                float(np.mean(self._session_durations_sec))
                if self._session_durations_sec
                else 0.0
            )

            return {
                "activations_total": self._activations_total,
                "double_clap_activations": self._double_clap_activations,
                "wake_word_activations": self._wake_word_activations,
                "manual_activations": self._manual_activations,
                "sessions_started": self._sessions_started,
                "sessions_completed": self._sessions_completed,
                "sessions_timed_out": self._sessions_timed_out,
                "speech_turns": self._speech_turns,
                "barge_ins": self._barge_ins,
                "state_transition_count": self._state_transition_count,
                "invalid_transition_count": self._invalid_transition_count,
                "stt_failures": self._stt_failures,
                "tts_failures": self._tts_failures,
                "average_session_duration_seconds": round(avg_duration, 2),
                "errors_count": self._errors_count,
            }

    def reset(self) -> None:
        """Reset all metrics counters."""
        with self._lock:
            self._activations_total = 0
            self._double_clap_activations = 0
            self._wake_word_activations = 0
            self._manual_activations = 0
            self._sessions_started = 0
            self._sessions_completed = 0
            self._sessions_timed_out = 0
            self._speech_turns = 0
            self._barge_ins = 0
            self._state_transition_count = 0
            self._invalid_transition_count = 0
            self._stt_failures = 0
            self._tts_failures = 0
            self._errors_count = 0
            self._session_durations_sec.clear()
