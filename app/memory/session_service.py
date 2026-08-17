"""High-level service manager for Phase 5.2 Session Memory & Active Session Context.

Phase 5.2 - Session Memory & Active Session Context Management
"""

import copy
import threading
import time
from typing import Any

from app.memory.service import ShortTermMemoryService
from app.memory.session_models import (
    SessionContext,
    SessionMemoryConfig,
    SessionMemorySnapshot,
    SessionTask,
    SessionWorkflow,
    TaskState,
)
from app.tools.execution.result_normalizer import SensitiveDataSanitizer


class SessionMemoryService:
    """Thread-safe manager for session-level active context, tasks, topics, and preferences."""

    def __init__(
        self,
        short_term_service: ShortTermMemoryService | None = None,
        config: SessionMemoryConfig | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self.config = config or SessionMemoryConfig()
        self.short_term_service = short_term_service or ShortTermMemoryService()
        self._sessions: dict[str, SessionContext] = {}

    def create_session_context(self, session_id: str) -> SessionContext:
        """Initialize or fetch session context for a canonical session_id."""
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionContext(session_id=session_id)
            ctx = self._sessions[session_id]
            ctx.last_activity = time.time()
            return ctx

    def get_session(self, session_id: str) -> SessionContext | None:
        """Retrieve session context container if active."""
        with self._lock:
            return self._sessions.get(session_id)

    def set_current_task(
        self,
        session_id: str,
        task_name: str,
        state: TaskState = TaskState.ACTIVE,
        metadata: dict[str, Any] | None = None,
    ) -> SessionTask:
        """Create or update current active session task."""
        clean_name = (
            SensitiveDataSanitizer.sanitize_text(task_name)
            if hasattr(SensitiveDataSanitizer, "sanitize_text")
            else task_name
        )
        sanitized_meta = SensitiveDataSanitizer.sanitize(metadata or {})

        with self._lock:
            ctx = self._get_or_create_unlocked(session_id)
            task = SessionTask(
                task_name=clean_name,
                state=state,
                updated_at=time.time(),
                metadata=sanitized_meta,
            )
            ctx.current_task = task
            ctx.last_activity = time.time()
            ctx.version += 1

            # Also push task into Short-Term Memory
            self.short_term_service.record_task(
                session_id, clean_name, metadata=sanitized_meta
            )
            return task

    def get_current_task(self, session_id: str) -> dict[str, Any] | None:
        """Fetch current active task in session."""
        with self._lock:
            ctx = self._sessions.get(session_id)
            if not ctx or not ctx.current_task:
                return None
            t = ctx.current_task
            return {
                "task_id": t.task_id,
                "task_name": t.task_name,
                "state": (
                    t.state.value if isinstance(t.state, TaskState) else str(t.state)
                ),
                "created_at": t.created_at,
                "updated_at": t.updated_at,
                "metadata": copy.deepcopy(t.metadata),
            }

    def clear_current_task(self, session_id: str) -> bool:
        """Clear active current task in session."""
        with self._lock:
            ctx = self._sessions.get(session_id)
            if ctx and ctx.current_task:
                ctx.current_task.state = TaskState.COMPLETED
                ctx.current_task = None
                ctx.last_activity = time.time()
                ctx.version += 1
                return True
            return False

    def set_current_topic(self, session_id: str, topic_name: str) -> str:
        """Set current conversational topic and maintain bounded topic history."""
        clean_topic = (
            SensitiveDataSanitizer.sanitize_text(topic_name)
            if hasattr(SensitiveDataSanitizer, "sanitize_text")
            else topic_name
        )
        with self._lock:
            ctx = self._get_or_create_unlocked(session_id)
            ctx.current_topic = clean_topic

            # Maintain recent topic history bounded to max_topics
            if (
                not ctx.recent_topics
                or ctx.recent_topics[-1].lower() != clean_topic.lower()
            ):
                ctx.recent_topics.append(clean_topic)
                if len(ctx.recent_topics) > self.config.max_topics:
                    ctx.recent_topics.pop(0)

            ctx.last_activity = time.time()
            ctx.version += 1
            return clean_topic

    def get_current_topic(self, session_id: str) -> str:
        """Fetch current active session topic."""
        with self._lock:
            ctx = self._sessions.get(session_id)
            return ctx.current_topic if ctx else "GENERAL"

    def add_entity(
        self,
        session_id: str,
        name: str,
        category: str = "GENERAL",
        identifier: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add active entity to session memory and short-term memory."""
        sanitized_meta = SensitiveDataSanitizer.sanitize(metadata or {})
        clean_name = (
            SensitiveDataSanitizer.sanitize_text(name)
            if hasattr(SensitiveDataSanitizer, "sanitize_text")
            else name
        )

        with self._lock:
            ctx = self._get_or_create_unlocked(session_id)
            entity_record = {
                "name": clean_name,
                "category": category,
                "identifier": identifier or clean_name,
                "last_seen": time.time(),
                "metadata": sanitized_meta,
            }

            # Update existing entity if present or append
            ctx.active_entities = [
                e
                for e in ctx.active_entities
                if e.get("name", "").lower() != clean_name.lower()
            ]
            ctx.active_entities.append(entity_record)

            if len(ctx.active_entities) > self.config.max_entities:
                ctx.active_entities.pop(0)

            ctx.last_activity = time.time()
            ctx.version += 1

            self.short_term_service.record_entity(
                session_id,
                clean_name,
                category=category,
                identifier=identifier,
                metadata=sanitized_meta,
            )

    def invalidate_entity(self, session_id: str, entity_id: str) -> bool:
        """Invalidate a stale entity in session context."""
        with self._lock:
            ctx = self._sessions.get(session_id)
            if not ctx:
                return False
            initial_len = len(ctx.active_entities)
            ctx.active_entities = [
                e
                for e in ctx.active_entities
                if e.get("identifier") != entity_id
                and e.get("name", "").lower() != entity_id.lower()
            ]
            invalidated = len(ctx.active_entities) < initial_len
            if invalidated:
                ctx.last_activity = time.time()
                ctx.version += 1

            self.short_term_service.invalidate_entity(session_id, entity_id)
            return invalidated

    def add_entity_relationship(
        self, session_id: str, parent_entity: str, child_entity: str
    ) -> None:
        """Define a relationship mapping between session entities (e.g. Project -> File)."""
        clean_parent = parent_entity.lower()
        clean_child = child_entity.lower()
        with self._lock:
            ctx = self._get_or_create_unlocked(session_id)
            if clean_parent not in ctx.entity_relationships:
                ctx.entity_relationships[clean_parent] = []
            if clean_child not in ctx.entity_relationships[clean_parent]:
                ctx.entity_relationships[clean_parent].append(clean_child)
            ctx.last_activity = time.time()
            ctx.version += 1

    def record_workflow(
        self,
        session_id: str,
        goal: str,
        current_step: int = 1,
        total_steps: int = 1,
        status: str = "COMPLETED",
        entities: list[str] | None = None,
    ) -> SessionWorkflow:
        """Record bounded workflow execution progress in session memory."""
        clean_goal = (
            SensitiveDataSanitizer.sanitize_text(goal)
            if hasattr(SensitiveDataSanitizer, "sanitize_text")
            else goal
        )
        wf = SessionWorkflow(
            goal=clean_goal,
            current_step=current_step,
            total_steps=total_steps,
            status=status,
            entities=entities or [],
            timestamp=time.time(),
        )

        with self._lock:
            ctx = self._get_or_create_unlocked(session_id)
            ctx.recent_workflows.append(wf)
            if len(ctx.recent_workflows) > self.config.max_workflows:
                ctx.recent_workflows.pop(0)
            ctx.last_activity = time.time()
            ctx.version += 1
            return wf

    def record_clarification(
        self, session_id: str, pending_request_dict: dict[str, Any]
    ) -> None:
        """Store pending clarification request in session context."""
        sanitized = SensitiveDataSanitizer.sanitize(pending_request_dict)
        with self._lock:
            ctx = self._get_or_create_unlocked(session_id)
            ctx.pending_request = sanitized
            ctx.last_activity = time.time()
            ctx.version += 1
            self.short_term_service.record_clarification(session_id, sanitized)

    def clear_clarification(self, session_id: str) -> bool:
        """Clear active clarification state in session context."""
        with self._lock:
            ctx = self._sessions.get(session_id)
            if ctx and ctx.pending_request:
                ctx.pending_request = None
                ctx.last_activity = time.time()
                ctx.version += 1
                return True
            return False

    def set_session_preference(self, session_id: str, key: str, value: Any) -> None:
        """Store temporary session preference (cleared when session ends)."""
        clean_val = (
            SensitiveDataSanitizer.sanitize_text(value)
            if isinstance(value, str)
            and hasattr(SensitiveDataSanitizer, "sanitize_text")
            else SensitiveDataSanitizer.sanitize(value)
        )
        with self._lock:
            ctx = self._get_or_create_unlocked(session_id)
            ctx.session_preferences[key] = clean_val
            if len(ctx.session_preferences) > self.config.max_session_preferences:
                # Evict oldest key
                first_key = next(iter(ctx.session_preferences))
                ctx.session_preferences.pop(first_key)
            ctx.last_activity = time.time()
            ctx.version += 1

    def get_session_preference(
        self, session_id: str, key: str, default: Any = None
    ) -> Any:
        """Fetch temporary session preference value."""
        with self._lock:
            ctx = self._sessions.get(session_id)
            if not ctx:
                return default
            return ctx.session_preferences.get(key, default)

    def create_snapshot(self, session_id: str) -> SessionMemorySnapshot:
        """Create a read-only, immutable snapshot of active session context."""
        with self._lock:
            ctx = self._sessions.get(session_id)
            if not ctx:
                return SessionMemorySnapshot(session_id=session_id)

            task_dict = (
                {
                    "task_id": ctx.current_task.task_id,
                    "task_name": ctx.current_task.task_name,
                    "state": (
                        ctx.current_task.state.value
                        if isinstance(ctx.current_task.state, TaskState)
                        else str(ctx.current_task.state)
                    ),
                    "metadata": copy.deepcopy(ctx.current_task.metadata),
                }
                if ctx.current_task
                else None
            )

            workflows_dict = [
                {
                    "workflow_id": wf.workflow_id,
                    "goal": wf.goal,
                    "current_step": wf.current_step,
                    "total_steps": wf.total_steps,
                    "status": wf.status,
                    "entities": list(wf.entities),
                }
                for wf in ctx.recent_workflows
            ]

            turns = self.short_term_service.get_recent_turns(session_id)

            return SessionMemorySnapshot(
                session_id=session_id,
                version=ctx.version,
                status=ctx.status,
                created_at=ctx.created_at,
                current_task=task_dict,
                current_topic=ctx.current_topic,
                recent_topics=list(ctx.recent_topics),
                active_entities=copy.deepcopy(ctx.active_entities),
                entity_relationships=copy.deepcopy(ctx.entity_relationships),
                pending_request=copy.deepcopy(ctx.pending_request),
                recent_workflows=workflows_dict,
                session_preferences=copy.deepcopy(ctx.session_preferences),
                turn_count=len(turns),
                last_activity=ctx.last_activity,
            )

    def end_session(self, session_id: str) -> bool:
        """End session context and flush session-level memory."""
        with self._lock:
            if session_id in self._sessions:
                ctx = self._sessions.pop(session_id)
                ctx.status = "ENDED"
                self.short_term_service.clear_session(session_id)
                return True
            return False

    def clear_all(self) -> None:
        """Clear all active session memory contexts."""
        with self._lock:
            self._sessions.clear()
            self.short_term_service.clear_all()

    # --- Unlocked helper ---

    def _get_or_create_unlocked(self, session_id: str) -> SessionContext:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionContext(session_id=session_id)
        return self._sessions[session_id]
