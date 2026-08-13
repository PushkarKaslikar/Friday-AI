"""Thread-safe active execution tracking and bounded execution history manager."""

import collections
import threading

from app.logging import logger
from app.tools.execution.execution_context import ExecutionContext
from app.tools.models.command import CommandState
from app.tools.models.result import ToolResult


class ExecutionTracker:
    """Thread-safe execution state tracker and bounded history store."""

    def __init__(self, history_limit: int = 100) -> None:
        self.history_limit = max(10, history_limit)
        self._lock = threading.RLock()
        self._active_executions: dict[str, ExecutionContext] = {}
        self._execution_history: collections.deque[ToolResult] = collections.deque(
            maxlen=self.history_limit
        )

    def register_execution(self, context: ExecutionContext) -> None:
        """Register active execution context."""
        with self._lock:
            self._active_executions[context.execution_id] = context

    def update_state(self, execution_id: str, new_state: CommandState) -> None:
        """Update active execution state."""
        with self._lock:
            context = self._active_executions.get(execution_id)
            if context:
                context.state = new_state

    def complete_execution(self, result: ToolResult) -> None:
        """Move execution from active tracking to bounded history."""
        with self._lock:
            self._active_executions.pop(result.execution_id, None)
            self._execution_history.append(result)

    def cancel_execution(
        self, execution_id: str, reason: str = "Cancelled by request"
    ) -> bool:
        """Signal cancellation token for target active execution."""
        with self._lock:
            context = self._active_executions.get(execution_id)
            if context:
                context.cancellation_token.request_cancellation(reason)
                logger.info(
                    f"ExecutionTracker: Cancellation requested for {execution_id}."
                )
                return True
        return False

    def get_execution(self, execution_id: str) -> ExecutionContext | None:
        """Retrieve active execution context by ID."""
        with self._lock:
            return self._active_executions.get(execution_id)

    def get_recent_executions(self, limit: int = 20) -> list[ToolResult]:
        """Get copy of recent execution history results."""
        with self._lock:
            items = list(self._execution_history)
            items.reverse()
            return items[:limit]

    @property
    def active_count(self) -> int:
        """Get count of currently active running executions."""
        with self._lock:
            return len(self._active_executions)

    def clear(self) -> None:
        """Clear active tracking and history."""
        with self._lock:
            self._active_executions.clear()
            self._execution_history.clear()
