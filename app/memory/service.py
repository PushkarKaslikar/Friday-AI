"""High-level service manager for Phase 5.1 Short-Term Memory.

Phase 5.1 - Short-Term Memory Foundation & Active Conversation Memory
"""

import json
from typing import Any

from app.memory.models import (
    MemoryEntry,
    MemoryEntryType,
    MemoryImportance,
    MemorySource,
    ShortTermMemoryConfig,
    ShortTermMemorySnapshot,
)
from app.memory.store import ShortTermMemoryStore
from app.tools.execution.result_normalizer import SensitiveDataSanitizer


class ShortTermMemoryService:
    """Service orchestrating short-term memory entry creation, sanitization, and queries."""

    def __init__(
        self,
        store: ShortTermMemoryStore | None = None,
        config: ShortTermMemoryConfig | None = None,
    ) -> None:
        self.config = config or ShortTermMemoryConfig()
        self.store = store or ShortTermMemoryStore(config=self.config)

    def record_user_message(
        self,
        session_id: str,
        text: str,
        turn_id: str = "",
        turn_number: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Sanitize and record a user message turn into short-term memory."""
        clean_text = (
            SensitiveDataSanitizer.sanitize_text(text)
            if hasattr(SensitiveDataSanitizer, "sanitize_text")
            else text
        )
        if len(clean_text) > self.config.max_entry_size:
            clean_text = clean_text[: self.config.max_entry_size] + "..."

        entry = MemoryEntry(
            session_id=session_id,
            turn_id=turn_id,
            turn_number=turn_number,
            type=MemoryEntryType.USER_MESSAGE,
            source=MemorySource.USER,
            importance=MemoryImportance.MEDIUM,
            content=clean_text,
            entity_metadata=SensitiveDataSanitizer.sanitize(metadata or {}),
        )
        return self.store.add_entry(session_id, entry)

    def record_assistant_message(
        self,
        session_id: str,
        text: str,
        turn_id: str = "",
        turn_number: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Sanitize and record an assistant response turn into short-term memory."""
        clean_text = (
            SensitiveDataSanitizer.sanitize_text(text)
            if hasattr(SensitiveDataSanitizer, "sanitize_text")
            else text
        )
        if len(clean_text) > self.config.max_entry_size:
            clean_text = clean_text[: self.config.max_entry_size] + "..."

        entry = MemoryEntry(
            session_id=session_id,
            turn_id=turn_id,
            turn_number=turn_number,
            type=MemoryEntryType.ASSISTANT_MESSAGE,
            source=MemorySource.ASSISTANT,
            importance=MemoryImportance.MEDIUM,
            content=clean_text,
            entity_metadata=SensitiveDataSanitizer.sanitize(metadata or {}),
        )
        return self.store.add_entry(session_id, entry)

    def record_entity(
        self,
        session_id: str,
        name: str,
        category: str = "GENERAL",
        identifier: str = "",
        source: MemorySource = MemorySource.USER,
        turn_number: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Record an active entity into short-term memory context."""
        clean_name = (
            SensitiveDataSanitizer.sanitize_text(name)
            if hasattr(SensitiveDataSanitizer, "sanitize_text")
            else name
        )
        meta = metadata.copy() if metadata else {}
        meta.update(
            {
                "name": clean_name,
                "category": category,
                "identifier": identifier or clean_name,
            }
        )
        sanitized_meta = SensitiveDataSanitizer.sanitize(meta)

        entry = MemoryEntry(
            session_id=session_id,
            turn_number=turn_number,
            type=MemoryEntryType.ENTITY,
            source=source,
            importance=MemoryImportance.HIGH,
            content=clean_name,
            entity_metadata=sanitized_meta,
        )
        return self.store.add_entry(session_id, entry)

    def record_tool_result(
        self,
        session_id: str,
        tool_name: str,
        status: str,
        result_data: Any,
        turn_number: int = 1,
    ) -> MemoryEntry:
        """Sanitize, bound, and record a tool execution result into short-term memory."""
        sanitized_res = SensitiveDataSanitizer.sanitize(result_data)
        res_str = (
            json.dumps(sanitized_res)
            if isinstance(sanitized_res, (dict, list))
            else str(sanitized_res)
        )

        if len(res_str) > self.config.max_tool_result_characters:
            res_str = res_str[: self.config.max_tool_result_characters] + "..."

        bounded_content = {
            "tool_name": tool_name,
            "status": status,
            "result_summary": res_str,
            "raw_sanitized": (
                sanitized_res
                if isinstance(sanitized_res, dict)
                else {"summary": res_str}
            ),
        }

        entry = MemoryEntry(
            session_id=session_id,
            turn_number=turn_number,
            type=MemoryEntryType.TOOL_RESULT,
            source=MemorySource.TOOL,
            importance=MemoryImportance.HIGH,
            content=bounded_content,
        )
        return self.store.add_entry(session_id, entry)

    def record_task(
        self,
        session_id: str,
        task_name: str,
        importance: MemoryImportance = MemoryImportance.HIGH,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Record an active task into short-term memory."""
        clean_task = (
            SensitiveDataSanitizer.sanitize_text(task_name)
            if hasattr(SensitiveDataSanitizer, "sanitize_text")
            else task_name
        )
        entry = MemoryEntry(
            session_id=session_id,
            type=MemoryEntryType.TASK,
            source=MemorySource.SYSTEM,
            importance=importance,
            content=clean_task,
            entity_metadata=SensitiveDataSanitizer.sanitize(metadata or {}),
        )
        return self.store.add_entry(session_id, entry)

    def record_clarification(
        self,
        session_id: str,
        pending_request_dict: dict[str, Any],
    ) -> MemoryEntry:
        """Record a pending clarification request into short-term memory."""
        sanitized_dict = SensitiveDataSanitizer.sanitize(pending_request_dict)
        entry = MemoryEntry(
            session_id=session_id,
            type=MemoryEntryType.CLARIFICATION,
            source=MemorySource.ASSISTANT,
            importance=MemoryImportance.HIGH,
            content=sanitized_dict,
        )
        return self.store.add_entry(session_id, entry)

    def record_correction(
        self,
        session_id: str,
        correction_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Record a user correction turn into short-term memory."""
        clean_text = (
            SensitiveDataSanitizer.sanitize_text(correction_text)
            if hasattr(SensitiveDataSanitizer, "sanitize_text")
            else correction_text
        )
        entry = MemoryEntry(
            session_id=session_id,
            type=MemoryEntryType.CORRECTION,
            source=MemorySource.USER,
            importance=MemoryImportance.HIGH,
            content=clean_text,
            entity_metadata=SensitiveDataSanitizer.sanitize(metadata or {}),
        )
        return self.store.add_entry(session_id, entry)

    def invalidate_entity(self, session_id: str, entity_id: str) -> bool:
        """Invalidate an entity in memory."""
        return self.store.invalidate_entity(session_id, entity_id)

    def create_snapshot(self, session_id: str) -> ShortTermMemorySnapshot:
        """Create read-only snapshot for downstream components."""
        return self.store.create_snapshot(session_id)

    def get_recent_turns(
        self, session_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Fetch recent turns within configured bounds."""
        return self.store.get_recent_turns(session_id, limit=limit)

    def get_active_entities(self, session_id: str) -> list[dict[str, Any]]:
        """Fetch active entities sorted by recency."""
        return self.store.get_active_entities(session_id)

    def get_current_task(self, session_id: str) -> dict[str, Any] | None:
        """Fetch current active task if available."""
        return self.store.get_current_task(session_id)

    def get_pending_request(self, session_id: str) -> dict[str, Any] | None:
        """Fetch pending clarification request if active."""
        return self.store.get_pending_request(session_id)

    def clear_session(self, session_id: str) -> bool:
        """Clear session memory context."""
        return self.store.clear_session(session_id)

    def clear_all(self) -> None:
        """Clear all session memory contexts."""
        self.store.clear_all()
