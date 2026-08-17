"""High-level service manager for Phase 5.3 Long-Term Persistent Memory.

Phase 5.3 - Long-Term Memory & Persistent Memory Foundation
"""

import threading
from typing import Any

from app.logging import logger
from app.memory.long_term_models import (
    LongTermMemoryConfig,
    LongTermMemoryEntry,
    MemoryCandidate,
    MemoryImportance,
    MemoryOperation,
    MemoryRequest,
    MemoryResult,
    MemorySource,
    MemoryType,
    UserControlState,
)
from app.memory.promotion_service import MemoryPromotionService
from app.memory.repository import IMemoryRepository


class LongTermMemoryService:
    """Thread-safe high-level manager orchestrating persistent memory CRUD, promotion, and request validation."""

    def __init__(
        self,
        repository: IMemoryRepository,
        promotion_service: MemoryPromotionService | None = None,
        config: LongTermMemoryConfig | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self.repository = repository
        self.promotion_service = promotion_service or MemoryPromotionService(repository)
        self.config = config or LongTermMemoryConfig()

    def remember(
        self,
        subject: str,
        content: str,
        memory_type: MemoryType = MemoryType.PREFERENCE,
        source: MemorySource = MemorySource.USER_EXPLICIT,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        metadata: dict[str, Any] | None = None,
        session_id: str = "",
    ) -> MemoryResult:
        """Store a structured memory entry into long-term persistent memory."""
        candidate = MemoryCandidate(
            memory_type=memory_type,
            subject=subject,
            content=content,
            source=source,
            importance=importance,
            session_id=session_id,
            explicit_request=(source == MemorySource.USER_EXPLICIT),
            metadata=metadata or {},
        )

        with self._lock:
            # Check maximum memory bounds
            current_count = self.repository.count(status=UserControlState.ACTIVE.value)
            if current_count >= self.config.max_total_memories:
                return MemoryResult(
                    status="REJECTED",
                    operation="REMEMBER",
                    message=f"Memory capacity limit reached ({self.config.max_total_memories} max)",
                    affected_count=0,
                )

            success, entry, msg = self.promotion_service.promote_candidate(candidate)
            if not success:
                return MemoryResult(
                    status="REJECTED",
                    operation="REMEMBER",
                    message=msg,
                    affected_count=0,
                )

            return MemoryResult(
                status="SUCCESS",
                memory_id=entry.memory_id if entry else None,
                operation="REMEMBER",
                message=msg,
                affected_count=1,
            )

    def handle_memory_request(self, request: MemoryRequest) -> MemoryResult:
        """Validate and execute a structured MemoryRequest produced by AI / Intent engine."""
        with self._lock:
            try:
                op = request.operation
                if op == MemoryOperation.REMEMBER:
                    return self.remember(
                        subject=request.subject,
                        content=request.content,
                        memory_type=request.memory_type,
                        source=request.source,
                        importance=request.importance,
                        metadata=request.metadata,
                    )
                elif op == MemoryOperation.FORGET:
                    return self.forget(
                        memory_type=(
                            request.memory_type.value
                            if hasattr(request.memory_type, "value")
                            else str(request.memory_type)
                        ),
                        subject=request.subject,
                        memory_id=request.memory_id,
                    )
                elif op == MemoryOperation.UPDATE:
                    if not request.memory_id:
                        return MemoryResult(
                            status="ERROR",
                            operation="UPDATE",
                            message="memory_id is required for UPDATE operation",
                            affected_count=0,
                        )
                    return self.update_memory(
                        memory_id=request.memory_id,
                        content=request.content,
                        metadata=request.metadata,
                    )
                elif op == MemoryOperation.GET:
                    mem = (
                        self.repository.get_memory(request.memory_id)
                        if request.memory_id
                        else self.repository.find_by_type_subject(
                            request.memory_type.value, request.subject
                        )
                    )
                    return MemoryResult(
                        status="SUCCESS" if mem else "NOT_FOUND",
                        memory_id=mem.memory_id if mem else None,
                        operation="GET",
                        message=(
                            f"Fetched memory for subject '{request.subject}'"
                            if mem
                            else "Not found"
                        ),
                        affected_count=1 if mem else 0,
                    )
                elif op == MemoryOperation.LIST:
                    memories = self.repository.list_memories(
                        memory_type=(
                            request.memory_type.value if request.memory_type else None
                        ),
                        subject=request.subject if request.subject else None,
                    )
                    return MemoryResult(
                        status="SUCCESS",
                        operation="LIST",
                        message=f"Retrieved {len(memories)} active memories",
                        affected_count=len(memories),
                    )

                return MemoryResult(
                    status="ERROR",
                    operation=str(op),
                    message=f"Unsupported operation '{op}'",
                    affected_count=0,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(f"LongTermMemoryService: Request execution error: {exc}")
                return MemoryResult(
                    status="ERROR",
                    operation=str(request.operation),
                    message=str(exc),
                    affected_count=0,
                )

    def get_memory(self, memory_id: str) -> LongTermMemoryEntry | None:
        """Fetch memory entry by memory_id."""
        with self._lock:
            return self.repository.get_memory(memory_id)

    def update_memory(
        self,
        memory_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryResult:
        """Update existing memory content or metadata."""
        with self._lock:
            existing = self.repository.get_memory(memory_id)
            if not existing:
                return MemoryResult(
                    status="NOT_FOUND",
                    operation="UPDATE",
                    message=f"Memory ID '{memory_id}' not found",
                    affected_count=0,
                )

            existing.content = content
            if metadata:
                existing.metadata.update(metadata)

            updated = self.repository.update_memory(existing)
            return MemoryResult(
                status="SUCCESS",
                memory_id=updated.memory_id if updated else memory_id,
                operation="UPDATE",
                message="Memory updated successfully",
                affected_count=1,
            )

    def forget(
        self,
        memory_type: str | None = None,
        subject: str | None = None,
        memory_id: str | None = None,
    ) -> MemoryResult:
        """Deactivate or remove memory entries matching filter criteria."""
        with self._lock:
            if memory_id:
                deleted = self.repository.delete_memory(memory_id, soft_delete=True)
                return MemoryResult(
                    status="SUCCESS" if deleted else "NOT_FOUND",
                    memory_id=memory_id,
                    operation="FORGET",
                    message="Memory deactivated" if deleted else "Memory ID not found",
                    affected_count=1 if deleted else 0,
                )

            memories = self.repository.list_memories(
                memory_type=memory_type,
                subject=subject,
                status=UserControlState.ACTIVE.value,
            )
            count = 0
            for m in memories:
                if self.repository.delete_memory(m.memory_id, soft_delete=True):
                    count += 1

            return MemoryResult(
                status="SUCCESS",
                operation="FORGET",
                message=f"Deactivated {count} memory records matching subject '{subject}'",
                affected_count=count,
            )

    def clear_all(self) -> MemoryResult:
        """Hard clear all stored memory records in persistent database."""
        with self._lock:
            cleared_count = self.repository.clear_all()
            return MemoryResult(
                status="SUCCESS",
                operation="CLEAR_ALL",
                message=f"Cleared {cleared_count} memory entries",
                affected_count=cleared_count,
            )

    def list_memories(
        self, memory_type: str | None = None, subject: str | None = None
    ) -> list[LongTermMemoryEntry]:
        """List active memories filtered by type or subject."""
        with self._lock:
            return self.repository.list_memories(
                memory_type=memory_type,
                subject=subject,
                status=UserControlState.ACTIVE.value,
            )

    def find_preference(self, subject: str) -> str | None:
        """Helper to fetch value of a preferred setting or subject."""
        with self._lock:
            mem = self.repository.find_by_type_subject(
                memory_type=MemoryType.PREFERENCE.value, subject=subject
            )
            return mem.content if mem else None

    def promote_candidate(self, candidate: MemoryCandidate) -> MemoryResult:
        """Promote a candidate from Session Memory into persistent Long-Term Memory."""
        with self._lock:
            success, entry, msg = self.promotion_service.promote_candidate(candidate)
            return MemoryResult(
                status="SUCCESS" if success else "REJECTED",
                memory_id=entry.memory_id if entry else None,
                operation="PROMOTE",
                message=msg,
                affected_count=1 if success else 0,
            )
