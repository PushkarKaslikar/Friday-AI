"""Background memory retention management and expiration cleanup service.

Phase 5.7 - Memory Privacy, Security, Governance & User Control
"""

import time
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from app.memory.long_term_service import LongTermMemoryService
    from app.memory.profile_service import UserProfileService
    from app.memory.semantic_service import SemanticMemoryService


class MemoryRetentionService:
    """Manages memory retention lifecycles and background expiration cleanup."""

    def __init__(
        self,
        long_term_service: "LongTermMemoryService | None" = None,
        user_profile_service: "UserProfileService | None" = None,
        semantic_service: "SemanticMemoryService | None" = None,
    ) -> None:
        self.long_term_service = long_term_service
        self.user_profile_service = user_profile_service
        self.semantic_service = semantic_service

    def is_expired(self, expires_at: float | None) -> bool:
        """Check whether a timestamp indicates expiration."""
        if not expires_at or expires_at <= 0:
            return False
        return time.time() >= expires_at

    def run_expiration_cleanup(self) -> int:
        """Scan active memory records, expire overdue records, and propagate cleanup across derived layers."""
        if not self.long_term_service:
            return 0

        now = time.time()
        expired_count = 0

        try:
            active_memories = self.long_term_service.list_memories()
            for mem in active_memories:
                if mem.expires_at and mem.expires_at > 0 and now >= mem.expires_at:
                    # Deactivate in SQLite
                    self.long_term_service.forget(memory_id=mem.memory_id)
                    expired_count += 1

            if expired_count > 0:
                if self.semantic_service:
                    self.semantic_service.rebuild_index()
                logger.info(
                    f"MemoryRetentionService: Successfully cleaned up {expired_count} expired memory records."
                )

            return expired_count
        except Exception as ex:  # noqa: BLE001
            logger.error(f"MemoryRetentionService: Retention cleanup error ({ex}).")
            return 0
