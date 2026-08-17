"""Central coordinator service for Memory Privacy, Security & User Control.

Phase 5.7 - Memory Privacy, Security, Governance & User Control
"""

import threading
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from loguru import logger

from app.memory.privacy_models import (
    MemoryPrivacyConfig,
    MemoryPrivacyDecision,
    PrivacySensitivity,
    PrivacyStatus,
)

if TYPE_CHECKING:
    from app.memory.long_term_service import LongTermMemoryService
    from app.memory.privacy_metrics import MemoryPrivacyMetrics
    from app.memory.privacy_policy import MemoryPrivacyPolicy
    from app.memory.profile_service import UserProfileService
    from app.memory.retention_service import MemoryRetentionService
    from app.memory.semantic_service import SemanticMemoryService


class IMemoryPrivacyService(ABC):
    """Abstract interface for Memory Privacy Subsystem."""

    @abstractmethod
    def evaluate_write(
        self,
        subject: str,
        content: str,
        memory_type: str = "",
        source: str = "USER_EXPLICIT",
    ) -> MemoryPrivacyDecision:
        """Evaluate write eligibility under privacy policy."""

    @abstractmethod
    def evaluate_read(
        self,
        subject: str,
        content: str,
        memory_type: str = "",
        sensitivity: PrivacySensitivity | None = None,
        is_explicit_request: bool = False,
    ) -> MemoryPrivacyDecision:
        """Evaluate read eligibility under privacy policy."""

    @abstractmethod
    def evaluate_index(
        self,
        subject: str,
        content: str,
        memory_type: str = "",
        sensitivity: PrivacySensitivity | None = None,
    ) -> MemoryPrivacyDecision:
        """Evaluate vector indexing eligibility under privacy policy."""

    @abstractmethod
    def evaluate_profile(
        self,
        subject: str,
        content: str,
        memory_type: str = "",
        sensitivity: PrivacySensitivity | None = None,
    ) -> MemoryPrivacyDecision:
        """Evaluate profile visibility under privacy policy."""

    @abstractmethod
    def forget_memory(
        self,
        subject: str = "",
        memory_type: str = "",
        memory_id: str | None = None,
    ) -> bool:
        """Execute end-to-end deletion propagation across SQLite, FAISS, and UserProfile."""

    @abstractmethod
    def clear_all_memory(self, confirmation: bool = True) -> bool:
        """Execute complete memory wipe across SQLite, FAISS, and UserProfile."""

    @abstractmethod
    def reconcile_memory_privacy(self) -> dict[str, Any]:
        """Detect and repair inconsistencies across derived layers."""

    @abstractmethod
    def get_subsystem_report(self) -> dict[str, Any]:
        """Return diagnostic health status."""


class MemoryPrivacyService(IMemoryPrivacyService):
    """Coordinates memory privacy governance across LongTermMemory, UserProfile, FAISS, and Memory Retrieval."""

    def __init__(
        self,
        policy: "MemoryPrivacyPolicy",
        retention_service: "MemoryRetentionService",
        metrics: "MemoryPrivacyMetrics",
        long_term_service: "LongTermMemoryService | None" = None,
        user_profile_service: "UserProfileService | None" = None,
        semantic_service: "SemanticMemoryService | None" = None,
        config: MemoryPrivacyConfig | None = None,
    ) -> None:
        self.policy = policy
        self.retention_service = retention_service
        self.metrics = metrics
        self.long_term_service = long_term_service
        self.user_profile_service = user_profile_service
        self.semantic_service = semantic_service
        self.config = config or MemoryPrivacyConfig()
        self._lock = threading.RLock()

    def get_subsystem_report(self) -> dict[str, Any]:
        """Return diagnostic status."""
        with self._lock:
            status = (
                PrivacyStatus.HEALTHY
                if (self.policy and self.config.enabled)
                else PrivacyStatus.DEGRADED
            )

            return {
                "status": status.value,
                "mode": self.config.mode.value,
                "persistence_enabled": self.config.allow_persistent_memory,
                "semantic_indexing_enabled": self.config.allow_semantic_indexing,
                "long_term_service_available": self.long_term_service is not None,
                "user_profile_service_available": self.user_profile_service is not None,
                "semantic_service_available": self.semantic_service is not None,
            }

    def evaluate_write(
        self,
        subject: str,
        content: str,
        memory_type: str = "",
        source: str = "USER_EXPLICIT",
    ) -> MemoryPrivacyDecision:
        """Evaluate write eligibility under privacy policy."""
        with self._lock:
            decision = self.policy.evaluate_write(
                subject=subject,
                content=content,
                memory_type=memory_type,
                source=source,
                mode_override=self.config.mode,
            )
            self.metrics.record_write_eval(
                allowed=decision.decision,
                restricted=(decision.sensitivity == PrivacySensitivity.RESTRICTED),
                confirmation=decision.requires_confirmation,
            )
            return decision

    def evaluate_read(
        self,
        subject: str,
        content: str,
        memory_type: str = "",
        sensitivity: PrivacySensitivity | None = None,
        is_explicit_request: bool = False,
    ) -> MemoryPrivacyDecision:
        """Evaluate read eligibility under privacy policy."""
        with self._lock:
            decision = self.policy.evaluate_read(
                subject=subject,
                content=content,
                memory_type=memory_type,
                sensitivity=sensitivity,
                mode_override=self.config.mode,
                is_explicit_request=is_explicit_request,
            )
            if not decision.decision:
                self.metrics.record_retrieval_block()
            return decision

    def evaluate_index(
        self,
        subject: str,
        content: str,
        memory_type: str = "",
        sensitivity: PrivacySensitivity | None = None,
    ) -> MemoryPrivacyDecision:
        """Evaluate vector indexing eligibility under privacy policy."""
        with self._lock:
            decision = self.policy.evaluate_index(
                subject=subject,
                content=content,
                memory_type=memory_type,
                sensitivity=sensitivity,
                mode_override=self.config.mode,
            )
            if not decision.decision:
                self.metrics.record_index_block()
            return decision

    def evaluate_profile(
        self,
        subject: str,
        content: str,
        memory_type: str = "",
        sensitivity: PrivacySensitivity | None = None,
    ) -> MemoryPrivacyDecision:
        """Evaluate profile visibility under privacy policy."""
        with self._lock:
            decision = self.policy.evaluate_profile(
                subject=subject,
                content=content,
                memory_type=memory_type,
                sensitivity=sensitivity,
                mode_override=self.config.mode,
            )
            if not decision.decision:
                self.metrics.record_profile_block()
            return decision

    def forget_memory(
        self,
        subject: str = "",
        memory_type: str = "",
        memory_id: str | None = None,
    ) -> bool:
        """Execute end-to-end deletion propagation across SQLite, FAISS, and UserProfile."""
        with self._lock:
            if not self.long_term_service:
                return False

            res = self.long_term_service.forget(
                memory_type=memory_type,
                subject=subject,
                memory_id=memory_id,
            )

            ok = res.status == "SUCCESS"
            if ok:
                self.metrics.record_deletion(res.affected_count or 1)

                # Rebuild FAISS index to purge deleted vector records
                if self.semantic_service:
                    self.semantic_service.rebuild_index()

            return ok

    def clear_all_memory(self, confirmation: bool = True) -> bool:
        """Execute complete memory wipe across SQLite, FAISS, and UserProfile."""
        if not confirmation:
            logger.warning(
                "MemoryPrivacyService: clear_all_memory rejected due to missing explicit confirmation."
            )
            return False

        with self._lock:
            try:
                # 1. Clear SQLite repository
                if self.long_term_service and self.long_term_service.repository:
                    self.long_term_service.repository.clear_all()

                # 2. Clear FAISS vector index
                if self.semantic_service and self.semantic_service.semantic_index:
                    self.semantic_service.semantic_index.clear()

                self.metrics.record_clear_all()
                logger.info(
                    "MemoryPrivacyService: Complete memory wipe successfully executed."
                )
                return True
            except Exception as ex:  # noqa: BLE001
                logger.error(f"MemoryPrivacyService: Clear-all wipe error ({ex}).")
                return False

    def reconcile_memory_privacy(self) -> dict[str, Any]:
        """Detect and repair inconsistencies across derived layers."""
        with self._lock:
            reconciled_vectors = 0
            reconciled_expired = 0

            # 1. Run retention cleanup
            if self.retention_service:
                reconciled_expired = self.retention_service.run_expiration_cleanup()

            # 2. Rebuild FAISS index from authoritative SQLite records
            if self.semantic_service:
                ok = self.semantic_service.rebuild_index()
                if ok:
                    reconciled_vectors = (
                        self.semantic_service.semantic_index.vector_count
                    )

            self.metrics.record_reconciliation()

            return {
                "status": "SUCCESS",
                "reconciled_expired_records": reconciled_expired,
                "reconciled_active_vectors": reconciled_vectors,
            }
