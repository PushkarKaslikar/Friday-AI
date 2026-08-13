"""Cooperative cancellation token for tool execution engine."""

import threading


class CancellationToken:
    """Thread-safe cancellation token supporting cooperative task cancellation."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._reason = ""

    def request_cancellation(
        self, reason: str = "User requested cancellation."
    ) -> None:
        """Flag cancellation requested."""
        self._reason = reason
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._event.is_set()

    @property
    def reason(self) -> str:
        """Get reason for cancellation."""
        return self._reason

    def throw_if_cancelled(self) -> None:
        """Raise RuntimeError if cancellation was requested.

        Raises:
            RuntimeError: If is_cancelled is True.
        """
        if self._event.is_set():
            raise RuntimeError(f"Operation cancelled: {self._reason}")
