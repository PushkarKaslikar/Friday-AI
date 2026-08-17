"""Bounded, thread-safe in-memory store for Phase 5.1 Short-Term Memory.

Phase 5.1 - Short-Term Memory Foundation & Active Conversation Memory
"""

import copy
import threading
import time
from typing import Any

from app.memory.models import (
    MemoryEntry,
    MemoryEntryType,
    MemoryImportance,
    ShortTermMemoryConfig,
    ShortTermMemorySnapshot,
)


class SessionMemoryContainer:
    """In-memory container holding short-term memory entries for a single session."""

    def __init__(self, session_id: str) -> None:
        self.session_id: str = session_id
        self.created_at: float = time.time()
        self.last_activity: float = time.time()
        self.version: int = 1
        self.entries: list[MemoryEntry] = []
        self.current_topic: str = "GENERAL"
        self.conversational_state: str = "NEW_REQUEST"


class ShortTermMemoryStore:
    """Thread-safe, bounded, in-memory store for short-term memory entries."""

    def __init__(self, config: ShortTermMemoryConfig | None = None) -> None:
        self._lock = threading.Lock()
        self.config = config or ShortTermMemoryConfig()
        self._sessions: dict[str, SessionMemoryContainer] = {}

    def get_or_create_session(self, session_id: str) -> SessionMemoryContainer:
        """Fetch existing session memory container or initialize new session."""
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionMemoryContainer(
                    session_id=session_id
                )
            container = self._sessions[session_id]
            container.last_activity = time.time()
            return container

    def get_session(self, session_id: str) -> SessionMemoryContainer | None:
        """Fetch active session container if present."""
        with self._lock:
            return self._sessions.get(session_id)

    def add_entry(self, session_id: str, entry: MemoryEntry) -> MemoryEntry:
        """Add a memory entry to active session context with bound enforcement."""
        with self._lock:
            container = self._get_or_create_session_unlocked(session_id)
            entry.session_id = session_id
            container.entries.append(entry)
            container.last_activity = time.time()
            container.version += 1
            self._evict_if_needed_unlocked(container)
            return entry

    def update_entry(
        self,
        session_id: str,
        entry_id: str,
        content: Any = None,
        importance: MemoryImportance | None = None,
        is_valid: bool | None = None,
        entity_metadata: dict[str, Any] | None = None,
        version: int | None = None,
    ) -> MemoryEntry | None:
        """Update an existing memory entry safely with stale update protection."""
        with self._lock:
            container = self._sessions.get(session_id)
            if not container:
                return None

            for entry in container.entries:
                if entry.entry_id == entry_id:
                    if version is not None and version < entry.version:
                        # Stale update protection
                        return None
                    if content is not None:
                        entry.content = content
                    if importance is not None:
                        entry.importance = importance
                    if is_valid is not None:
                        entry.is_valid = is_valid
                    if entity_metadata is not None:
                        entry.entity_metadata.update(entity_metadata)
                    entry.version += 1
                    entry.timestamp = time.time()
                    container.last_activity = time.time()
                    container.version += 1
                    return entry
            return None

    def get_entry(self, session_id: str, entry_id: str) -> MemoryEntry | None:
        """Retrieve a specific memory entry by ID."""
        with self._lock:
            container = self._sessions.get(session_id)
            if not container:
                return None
            for entry in container.entries:
                if entry.entry_id == entry_id:
                    return copy.deepcopy(entry)
            return None

    def remove_entry(self, session_id: str, entry_id: str) -> bool:
        """Remove a memory entry from session context."""
        with self._lock:
            container = self._sessions.get(session_id)
            if not container:
                return False
            initial_len = len(container.entries)
            container.entries = [e for e in container.entries if e.entry_id != entry_id]
            removed = len(container.entries) < initial_len
            if removed:
                container.last_activity = time.time()
                container.version += 1
            return removed

    def get_recent_entries(
        self, session_id: str, limit: int | None = None
    ) -> list[MemoryEntry]:
        """Retrieve recent memory entries sorted chronologically."""
        with self._lock:
            container = self._sessions.get(session_id)
            if not container:
                return []
            lim = limit if limit is not None else self.config.max_entries
            valid_entries = [e for e in container.entries if e.is_valid]
            return [copy.deepcopy(e) for e in valid_entries[-lim:]]

    def get_recent_turns(
        self, session_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Retrieve bounded recent user/assistant turns."""
        with self._lock:
            container = self._sessions.get(session_id)
            if not container:
                return []

            lim = min(limit, self.config.max_turns)
            turn_entries = [
                e
                for e in container.entries
                if e.is_valid
                and e.type
                in (MemoryEntryType.USER_MESSAGE, MemoryEntryType.ASSISTANT_MESSAGE)
            ]

            results = []
            for e in turn_entries[-lim:]:
                text_content = (
                    str(e.content)
                    if isinstance(e.content, str)
                    else (
                        str(e.content.get("text", ""))
                        if isinstance(e.content, dict)
                        else str(e.content)
                    )
                )

                # Truncate text content if individual entry exceeds max_entry_size
                if len(text_content) > self.config.max_entry_size:
                    text_content = text_content[: self.config.max_entry_size] + "..."

                results.append(
                    {
                        "turn_id": e.turn_id,
                        "turn_number": e.turn_number,
                        "speaker": (
                            "USER"
                            if e.type == MemoryEntryType.USER_MESSAGE
                            else "ASSISTANT"
                        ),
                        "text": text_content,
                        "timestamp": e.timestamp,
                    }
                )
            return results

    def get_active_entities(self, session_id: str) -> list[dict[str, Any]]:
        """Retrieve active valid entities sorted by recency."""
        with self._lock:
            container = self._sessions.get(session_id)
            if not container:
                return []

            entity_entries = [
                e
                for e in container.entries
                if e.is_valid and e.type == MemoryEntryType.ENTITY
            ]

            # Filter unique entities by identifier/name keeping the latest
            entities_by_key: dict[str, dict[str, Any]] = {}
            for e in entity_entries:
                key = str(
                    e.entity_metadata.get("identifier")
                    or e.entity_metadata.get("name")
                    or e.content
                ).lower()
                entities_by_key[key] = {
                    "entity_id": e.entry_id,
                    "category": e.entity_metadata.get("category", "GENERAL"),
                    "name": e.entity_metadata.get("name", str(e.content)),
                    "identifier": e.entity_metadata.get("identifier", ""),
                    "source": e.source.value,
                    "turn_number": e.turn_number,
                    "last_seen": e.timestamp,
                }

            sorted_entities = sorted(
                entities_by_key.values(), key=lambda x: x["last_seen"], reverse=True
            )
            return sorted_entities[: self.config.max_entities]

    def get_current_task(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve the latest active task entry."""
        with self._lock:
            container = self._sessions.get(session_id)
            if not container:
                return None
            task_entries = [
                e
                for e in container.entries
                if e.is_valid and e.type == MemoryEntryType.TASK
            ]
            if not task_entries:
                return None
            latest = task_entries[-1]
            return {
                "entry_id": latest.entry_id,
                "task_name": str(latest.content),
                "importance": latest.importance.value,
                "metadata": latest.entity_metadata,
                "timestamp": latest.timestamp,
            }

    def get_pending_request(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve the latest valid pending clarification request."""
        with self._lock:
            container = self._sessions.get(session_id)
            if not container:
                return None
            clarification_entries = [
                e
                for e in container.entries
                if e.is_valid and e.type == MemoryEntryType.CLARIFICATION
            ]
            if not clarification_entries:
                return None
            latest = clarification_entries[-1]
            return (
                latest.content
                if isinstance(latest.content, dict)
                else {"prompt": str(latest.content)}
            )

    def invalidate_entity(self, session_id: str, entity_id: str) -> bool:
        """Invalidate an entity in memory (e.g. app closed, file deleted)."""
        with self._lock:
            container = self._sessions.get(session_id)
            if not container:
                return False
            updated = False
            for entry in container.entries:
                if (
                    entry.entry_id == entity_id
                    or entry.entity_metadata.get("identifier") == entity_id
                    or entry.entity_metadata.get("name", "").lower()
                    == entity_id.lower()
                ):
                    entry.is_valid = False
                    updated = True
            if updated:
                container.last_activity = time.time()
                container.version += 1
            return updated

    def create_snapshot(self, session_id: str) -> ShortTermMemorySnapshot:
        """Create a read-only, immutable snapshot of active short-term context."""
        with self._lock:
            container = self._sessions.get(session_id)
            if not container:
                return ShortTermMemorySnapshot(session_id=session_id)

            recent_turns = self._get_recent_turns_unlocked(
                container, limit=self.config.max_turns
            )
            active_entities = self._get_active_entities_unlocked(container)
            current_task = self._get_current_task_unlocked(container)
            pending_clarification = self._get_pending_request_unlocked(container)
            recent_tool_results = self._get_recent_tool_results_unlocked(container)

            return ShortTermMemorySnapshot(
                session_id=session_id,
                version=container.version,
                created_at=time.time(),
                recent_turns=recent_turns,
                active_entities=active_entities,
                current_task=current_task,
                pending_clarification=pending_clarification,
                recent_tool_results=recent_tool_results,
                current_topic=container.current_topic,
                conversational_state=container.conversational_state,
            )

    def evict(self, session_id: str) -> int:
        """Manually trigger eviction of old or low-priority memory entries."""
        with self._lock:
            container = self._sessions.get(session_id)
            if not container:
                return 0
            return self._evict_if_needed_unlocked(container)

    def clear_session(self, session_id: str) -> bool:
        """Clear memory for a specific session."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def clear_all(self) -> None:
        """Clear all session memory contexts."""
        with self._lock:
            self._sessions.clear()

    # --- Unlocked internal helpers ---

    def _get_or_create_session_unlocked(
        self, session_id: str
    ) -> SessionMemoryContainer:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionMemoryContainer(session_id=session_id)
        return self._sessions[session_id]

    def _evict_if_needed_unlocked(self, container: SessionMemoryContainer) -> int:
        evicted_count = 0
        while len(container.entries) > self.config.max_entries:
            # Find candidate for eviction:
            # 1. First pick LOW importance entries
            low_idx = next(
                (
                    i
                    for i, e in enumerate(container.entries)
                    if e.importance == MemoryImportance.LOW and e.is_valid
                ),
                None,
            )
            if low_idx is not None:
                container.entries.pop(low_idx)
                evicted_count += 1
                continue

            # 2. Pick MEDIUM importance entries
            med_idx = next(
                (
                    i
                    for i, e in enumerate(container.entries)
                    if e.importance == MemoryImportance.MEDIUM and e.is_valid
                ),
                None,
            )
            if med_idx is not None:
                container.entries.pop(med_idx)
                evicted_count += 1
                continue

            # 3. Fallback: FIFO eviction of oldest entry
            container.entries.pop(0)
            evicted_count += 1

        return evicted_count

    def _get_recent_turns_unlocked(
        self, container: SessionMemoryContainer, limit: int
    ) -> list[dict[str, Any]]:
        lim = min(limit, self.config.max_turns)
        turn_entries = [
            e
            for e in container.entries
            if e.is_valid
            and e.type
            in (MemoryEntryType.USER_MESSAGE, MemoryEntryType.ASSISTANT_MESSAGE)
        ]

        results = []
        for e in turn_entries[-lim:]:
            text_content = (
                str(e.content)
                if isinstance(e.content, str)
                else (
                    str(e.content.get("text", ""))
                    if isinstance(e.content, dict)
                    else str(e.content)
                )
            )

            if len(text_content) > self.config.max_entry_size:
                text_content = text_content[: self.config.max_entry_size] + "..."

            results.append(
                {
                    "turn_id": e.turn_id,
                    "turn_number": e.turn_number,
                    "speaker": (
                        "USER"
                        if e.type == MemoryEntryType.USER_MESSAGE
                        else "ASSISTANT"
                    ),
                    "text": text_content,
                    "timestamp": e.timestamp,
                }
            )
        return results

    def _get_active_entities_unlocked(
        self, container: SessionMemoryContainer
    ) -> list[dict[str, Any]]:
        entity_entries = [
            e
            for e in container.entries
            if e.is_valid and e.type == MemoryEntryType.ENTITY
        ]

        entities_by_key: dict[str, dict[str, Any]] = {}
        for e in entity_entries:
            key = str(
                e.entity_metadata.get("identifier")
                or e.entity_metadata.get("name")
                or e.content
            ).lower()
            entities_by_key[key] = {
                "entity_id": e.entry_id,
                "category": e.entity_metadata.get("category", "GENERAL"),
                "name": e.entity_metadata.get("name", str(e.content)),
                "identifier": e.entity_metadata.get("identifier", ""),
                "source": e.source.value,
                "turn_number": e.turn_number,
                "last_seen": e.timestamp,
            }

        sorted_entities = sorted(
            entities_by_key.values(), key=lambda x: x["last_seen"], reverse=True
        )
        return sorted_entities[: self.config.max_entities]

    def _get_current_task_unlocked(
        self, container: SessionMemoryContainer
    ) -> dict[str, Any] | None:
        task_entries = [
            e
            for e in container.entries
            if e.is_valid and e.type == MemoryEntryType.TASK
        ]
        if not task_entries:
            return None
        latest = task_entries[-1]
        return {
            "entry_id": latest.entry_id,
            "task_name": str(latest.content),
            "importance": latest.importance.value,
            "metadata": latest.entity_metadata,
            "timestamp": latest.timestamp,
        }

    def _get_pending_request_unlocked(
        self, container: SessionMemoryContainer
    ) -> dict[str, Any] | None:
        clarification_entries = [
            e
            for e in container.entries
            if e.is_valid and e.type == MemoryEntryType.CLARIFICATION
        ]
        if not clarification_entries:
            return None
        latest = clarification_entries[-1]
        return (
            latest.content
            if isinstance(latest.content, dict)
            else {"prompt": str(latest.content)}
        )

    def _get_recent_tool_results_unlocked(
        self, container: SessionMemoryContainer
    ) -> list[dict[str, Any]]:
        tool_entries = [
            e
            for e in container.entries
            if e.is_valid and e.type == MemoryEntryType.TOOL_RESULT
        ]
        results = []
        for e in tool_entries[-5:]:
            res_content = (
                e.content if isinstance(e.content, dict) else {"result": str(e.content)}
            )
            results.append(res_content)
        return results
