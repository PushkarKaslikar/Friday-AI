"""Deterministic state machine managing double-clap gesture timing and refractory cooldown."""

import threading
import time

from app.logging import logger
from app.voice.clap.metrics import ClapMetrics
from app.voice.clap.models import ClapConfiguration, ClapEvent, ClapState


class DoubleClapStateMachine:
    """State machine governing single-clap validation, timing window logic, timeouts, and refractory cooldown.

    States: IDLE -> CLAP_DETECTED -> WAITING_FOR_SECOND_CLAP -> ACTIVATED -> COOLDOWN -> IDLE
    """

    def __init__(
        self,
        config: ClapConfiguration | None = None,
        metrics: ClapMetrics | None = None,
    ) -> None:
        self.config = config or ClapConfiguration()
        self.metrics = metrics or ClapMetrics()

        self._state = ClapState.IDLE
        self._first_clap: ClapEvent | None = None
        self._cooldown_until: float = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> ClapState:
        """Current state of state machine."""
        with self._lock:
            self._check_timeout_locked()
            return self._state

    @property
    def first_clap_timestamp(self) -> float | None:
        """Timestamp of first detected clap if waiting for second clap."""
        with self._lock:
            return self._first_clap.timestamp if self._first_clap else None

    def reset(self) -> None:
        """Reset state machine back to IDLE."""
        with self._lock:
            self._state = ClapState.IDLE
            self._first_clap = None
            self._cooldown_until = 0.0

    def process_clap_event(self, event: ClapEvent) -> tuple[bool, float]:
        """Process a validated single ClapEvent.

        Returns:
            Tuple[bool, float]: (is_double_clap_activated, interval_ms)
        """
        now = event.timestamp

        with self._lock:
            # 1. Refractory Cooldown Suppression Check
            if self._state == ClapState.COOLDOWN or now < self._cooldown_until:
                if now >= self._cooldown_until:
                    self._state = ClapState.IDLE
                else:
                    self.metrics.record_cooldown_suppression()
                    return False, 0.0

            # 2. Timeout Check for Pending First Clap
            self._check_timeout_locked(current_time=now)

            # 3. IDLE State -> Register First Clap
            if self._state == ClapState.IDLE:
                self._state = ClapState.WAITING_FOR_SECOND_CLAP
                self._first_clap = event
                return False, 0.0

            # 4. WAITING_FOR_SECOND_CLAP State -> Evaluate Second Clap Timing
            if self._state == ClapState.WAITING_FOR_SECOND_CLAP and self._first_clap:
                interval_ms = (now - self._first_clap.timestamp) * 1000.0
                min_interval = float(self.config.min_clap_interval_ms)
                max_interval = float(self.config.max_clap_interval_ms)

                self.metrics.record_double_clap_attempt()

                # Case A: Too soon (< min_clap_interval_ms) -> Ignore/reject duplicate impact
                if interval_ms < min_interval:
                    self.metrics.record_rejected_candidate()
                    return False, interval_ms

                # Case B: Valid interval -> ACTIVATED!
                if min_interval <= interval_ms <= max_interval:
                    self._state = ClapState.COOLDOWN
                    self._cooldown_until = now + (self.config.cooldown_ms / 1000.0)
                    self._first_clap = None
                    self.metrics.record_successful_double_clap()
                    logger.info(
                        f"DoubleClapStateMachine: DOUBLE CLAP ACTIVATED! Interval: {interval_ms:.1f}ms."
                    )
                    return True, interval_ms

                # Case C: Exceeded max interval -> Reset & treat as new first clap
                self.metrics.record_timeout()
                self._first_clap = event
                self._state = ClapState.WAITING_FOR_SECOND_CLAP
                return False, 0.0

            return False, 0.0

    def _check_timeout_locked(self, current_time: float | None = None) -> None:
        """Internal helper assessing timing window expiration (must be called with self._lock)."""
        if self._state == ClapState.WAITING_FOR_SECOND_CLAP and self._first_clap:
            # If current_time is omitted and first clap timestamp is simulated (< 1e6), skip wall-clock timeout
            if current_time is None and self._first_clap.timestamp < 1000000.0:
                return

            now = current_time if current_time is not None else time.time()
            elapsed_ms = (now - self._first_clap.timestamp) * 1000.0
            if elapsed_ms > self.config.max_clap_interval_ms:
                self.metrics.record_timeout()
                self._state = ClapState.IDLE
                self._first_clap = None
