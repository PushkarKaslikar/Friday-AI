"""Bounded, thread-safe in-memory conversation store for Phase 3.8.

Phase 3.8 - Conversation Manager, Session Context & Short-Term Memory
"""

import threading
import time
from typing import Any

from app.voice.conversation.manager_models import (
    ContextSnapshot,
    ConversationTurn,
    PendingRequest,
    SessionStatus,
    TrackedEntity,
)


class SessionContextContainer:
    """In-memory container holding short-term conversational context for a session."""

    def __init__(self, session_id: str, activation_source: str = "WAKE_WORD") -> None:
        self.session_id: str = session_id
        self.activation_source: str = activation_source
        self.created_at: float = time.time()
        self.last_activity: float = time.time()
        self.status: SessionStatus = SessionStatus.ACTIVE
        self.turns: list[ConversationTurn] = []
        self.entities: list[TrackedEntity] = []
        self.recent_commands: list[dict[str, Any]] = []
        self.recent_results: list[dict[str, Any]] = []
        self.pending_request: PendingRequest | None = None
        self.current_topic: str = "GENERAL"
        self.context_version: int = 1
        self.snapshot: ContextSnapshot | None = None


class InMemConversationStore:
    """Thread-safe in-memory store for session contexts."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, SessionContextContainer] = {}

    def get_or_create_session(
        self,
        session_id: str,
        activation_source: str = "WAKE_WORD",
    ) -> SessionContextContainer:
        """Fetch existing session container or initialize new session context."""
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionContextContainer(
                    session_id=session_id, activation_source=activation_source
                )
            container = self._sessions[session_id]
            container.last_activity = time.time()
            return container

    def get_session(self, session_id: str) -> SessionContextContainer | None:
        """Fetch active session container if present."""
        with self._lock:
            return self._sessions.get(session_id)

    def add_turn(self, session_id: str, turn: ConversationTurn) -> None:
        """Add a conversation turn to active session context."""
        with self._lock:
            if session_id in self._sessions:
                container = self._sessions[session_id]
                container.turns.append(turn)
                container.last_activity = time.time()
                container.context_version += 1

    def add_entity(self, session_id: str, entity: TrackedEntity) -> None:
        """Add or update a tracked entity in session context."""
        with self._lock:
            if session_id in self._sessions:
                container = self._sessions[session_id]
                # Replace existing entity with same name/identifier if present
                container.entities = [
                    e
                    for e in container.entities
                    if e.name.lower() != entity.name.lower()
                ]
                container.entities.append(entity)
                container.last_activity = time.time()
                container.context_version += 1

    def add_tool_result(
        self, session_id: str, command: dict[str, Any], result: dict[str, Any]
    ) -> None:
        """Record command execution and result in short-term context."""
        with self._lock:
            if session_id in self._sessions:
                container = self._sessions[session_id]
                container.recent_commands.append(command)
                container.recent_results.append(result)
                container.last_activity = time.time()
                container.context_version += 1

    def end_session(
        self, session_id: str, reason: str = "ended"
    ) -> SessionContextContainer | None:
        """Flush and remove session container from memory."""
        with self._lock:
            if session_id in self._sessions:
                container = self._sessions.pop(session_id)
                container.status = (
                    SessionStatus.ENDED
                    if reason != "session_timeout"
                    else SessionStatus.TIMED_OUT
                )
                return container
            return None

    def clear_all(self) -> None:
        """Clear all stored sessions from memory."""
        with self._lock:
            self._sessions.clear()
