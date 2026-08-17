"""Thread-safe operational telemetry for Memory Privacy Subsystem.

Phase 5.7 - Memory Privacy, Security, Governance & User Control
"""

import threading


class MemoryPrivacyMetrics:
    """Thread-safe telemetry collector for Phase 5.7 Memory Privacy & Governance."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._write_evaluations = 0
        self._writes_allowed = 0
        self._writes_denied = 0
        self._confirmation_requests = 0
        self._restricted_blocks = 0
        self._retention_expirations = 0
        self._retrieval_blocks = 0
        self._indexing_blocks = 0
        self._profile_blocks = 0
        self._deletions = 0
        self._clear_all_ops = 0
        self._reconciliations = 0

    def record_write_eval(
        self, allowed: bool, restricted: bool = False, confirmation: bool = False
    ) -> None:
        """Record outcome of a write privacy evaluation."""
        with self._lock:
            self._write_evaluations += 1
            if allowed:
                self._writes_allowed += 1
            else:
                self._writes_denied += 1
            if restricted:
                self._restricted_blocks += 1
            if confirmation:
                self._confirmation_requests += 1

    def record_retrieval_block(self) -> None:
        """Record a retrieval block event."""
        with self._lock:
            self._retrieval_blocks += 1

    def record_index_block(self) -> None:
        """Record an indexing block event."""
        with self._lock:
            self._indexing_blocks += 1

    def record_profile_block(self) -> None:
        """Record a profile visibility block event."""
        with self._lock:
            self._profile_blocks += 1

    def record_expiration(self, count: int = 1) -> None:
        """Record retention expiration cleanup count."""
        with self._lock:
            self._retention_expirations += count

    def record_deletion(self, count: int = 1) -> None:
        """Record memory deletion event."""
        with self._lock:
            self._deletions += count

    def record_clear_all(self) -> None:
        """Record clear-all memory wipe operation."""
        with self._lock:
            self._clear_all_ops += 1

    def record_reconciliation(self) -> None:
        """Record reconciliation execution."""
        with self._lock:
            self._reconciliations += 1

    def snapshot(self) -> dict:
        """Return a thread-safe snapshot of privacy telemetry."""
        with self._lock:
            return {
                "write_evaluations": self._write_evaluations,
                "writes_allowed": self._writes_allowed,
                "writes_denied": self._writes_denied,
                "confirmation_requests": self._confirmation_requests,
                "restricted_blocks": self._restricted_blocks,
                "retention_expirations": self._retention_expirations,
                "retrieval_blocks": self._retrieval_blocks,
                "indexing_blocks": self._indexing_blocks,
                "profile_blocks": self._profile_blocks,
                "deletions": self._deletions,
                "clear_all_ops": self._clear_all_ops,
                "reconciliations": self._reconciliations,
            }
