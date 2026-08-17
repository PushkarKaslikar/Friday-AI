"""Memory promotion service for validating, sanitizing, and promoting session candidates to long-term storage.

Phase 5.3 - Long-Term Memory & Persistent Memory Foundation
"""

import time
from typing import ClassVar

from app.memory.long_term_models import (
    LongTermMemoryEntry,
    MemoryCandidate,
    UserControlState,
)
from app.memory.repository import IMemoryRepository
from app.tools.execution.result_normalizer import SensitiveDataSanitizer


class MemoryPromotionService:
    """Evaluates candidates for persistent promotion, enforcing deduplication, conflict resolution, and secret protection."""

    SECRET_KEYWORDS: ClassVar[set[str]] = {
        "password",
        "passcode",
        "api_key",
        "apikey",
        "secret",
        "private_key",
        "token",
        "bearer",
        "cookie",
        "auth_header",
        "credentials",
    }

    def __init__(self, repository: IMemoryRepository) -> None:
        self.repository = repository

    def is_sensitive_secret(self, text: str, subject: str = "") -> bool:
        """Check if candidate content or subject contains secret credentials."""
        combined = f"{subject} {text}".lower()
        return any(k in combined for k in self.SECRET_KEYWORDS)

    def promote_candidate(
        self, candidate: MemoryCandidate
    ) -> tuple[bool, LongTermMemoryEntry | None, str]:
        """Validate candidate and promote into persistent long-term storage."""
        # 1. Security & Credential Protection Floor
        if self.is_sensitive_secret(candidate.content, candidate.subject):
            return (
                False,
                None,
                "Rejected: Contains sensitive credentials or secret token",
            )

        # 2. Check explicitly sanitized content
        clean_content = (
            SensitiveDataSanitizer.sanitize_text(candidate.content)
            if hasattr(SensitiveDataSanitizer, "sanitize_text")
            else candidate.content
        )
        clean_subject = candidate.subject.strip().lower()

        if not clean_subject or not clean_content:
            return False, None, "Rejected: Empty subject or content"

        # 3. Deduplication Check (Same type, subject, and content already ACTIVE)
        type_str = (
            candidate.memory_type.value
            if hasattr(candidate.memory_type, "value")
            else str(candidate.memory_type)
        )
        existing = self.repository.find_by_type_subject(
            memory_type=type_str,
            subject=clean_subject,
            status=UserControlState.ACTIVE.value,
        )

        if existing:
            if existing.content.strip().lower() == clean_content.strip().lower():
                return (
                    True,
                    existing,
                    "No-op: Duplicate active memory record already exists",
                )

            # 4. Conflict Resolution (Updating existing preference subject with new value)
            existing.content = clean_content
            existing.confidence = candidate.confidence
            existing.source = candidate.source
            existing.importance = candidate.importance
            if candidate.metadata:
                existing.metadata = {**(existing.metadata or {}), **candidate.metadata}
            existing.updated_at = time.time()
            updated = self.repository.update_memory(existing)
            return (
                True,
                updated,
                "Updated: Resolved conflict by updating existing active memory record",
            )

        # 5. Create new LongTermMemoryEntry
        new_entry = LongTermMemoryEntry(
            memory_type=candidate.memory_type,
            subject=clean_subject,
            content=clean_content,
            source=candidate.source,
            confidence=candidate.confidence,
            importance=candidate.importance,
            user_control_state=UserControlState.ACTIVE,
            sensitivity=candidate.sensitivity,
            session_origin=candidate.session_id,
            metadata=candidate.metadata or {},
            created_at=time.time(),
            updated_at=time.time(),
        )

        saved = self.repository.add_memory(new_entry)
        return (
            True,
            saved,
            "Success: Promoted candidate into long-term persistent memory",
        )
