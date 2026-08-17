"""Central coordinator service for context-aware memory retrieval.

Phase 5.6 - Memory Retrieval & Relevant Context Engine
"""

import threading
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from loguru import logger

from app.memory.retrieval_models import (
    CandidateMemory,
    MemoryRetrievalConfig,
    MemoryRetrievalRequest,
    MemoryRetrievalResult,
    RetrievalStatus,
)

if TYPE_CHECKING:
    from app.memory.context_builder import MemoryContextBuilder
    from app.memory.long_term_service import LongTermMemoryService
    from app.memory.profile_service import UserProfileService
    from app.memory.query_builder import MemoryQueryBuilder
    from app.memory.ranking_service import MemoryRankingService
    from app.memory.retrieval_metrics import MemoryRetrievalMetrics
    from app.memory.retrieval_policy import MemoryRetrievalPolicy
    from app.memory.semantic_service import SemanticMemoryService
    from app.memory.session_service import SessionMemoryService


class IMemoryRetrievalService(ABC):
    """Abstract interface for Memory Retrieval Subsystem."""

    @abstractmethod
    def retrieve_memory_context(
        self, request: MemoryRetrievalRequest
    ) -> MemoryRetrievalResult:
        """Execute memory retrieval and return formatted result."""

    @abstractmethod
    def get_subsystem_report(self) -> dict:
        """Return diagnostic status of the retrieval service."""


class MemoryRetrievalService(IMemoryRetrievalService):
    """Coordinates hybrid memory retrieval across Session, Profile, and Semantic vector memory."""

    def __init__(
        self,
        long_term_service: "LongTermMemoryService | None",
        user_profile_service: "UserProfileService | None",
        session_service: "SessionMemoryService | None",
        semantic_service: "SemanticMemoryService | None",
        policy: "MemoryRetrievalPolicy",
        query_builder: "MemoryQueryBuilder",
        ranking_service: "MemoryRankingService",
        context_builder: "MemoryContextBuilder",
        metrics: "MemoryRetrievalMetrics",
        config: MemoryRetrievalConfig | None = None,
    ) -> None:
        self.long_term_service = long_term_service
        self.user_profile_service = user_profile_service
        self.session_service = session_service
        self.semantic_service = semantic_service
        self.policy = policy
        self.query_builder = query_builder
        self.ranking_service = ranking_service
        self.context_builder = context_builder
        self.metrics = metrics
        self.config = config or MemoryRetrievalConfig()
        self._lock = threading.RLock()

    def get_subsystem_report(self) -> dict:
        """Return diagnostic health status."""
        with self._lock:
            has_sem = (
                self.semantic_service is not None
                and self.semantic_service.semantic_index.is_ready
            )
            has_lt = self.long_term_service is not None
            has_prof = self.user_profile_service is not None
            has_sess = self.session_service is not None

            status = "HEALTHY" if (has_lt and (has_sem or has_prof)) else "DEGRADED"

            return {
                "status": status,
                "policy_mode": "AUTO" if self.config.auto_trigger else "MANUAL",
                "semantic_service_available": has_sem,
                "long_term_service_available": has_lt,
                "user_profile_service_available": has_prof,
                "session_service_available": has_sess,
                "max_results": self.config.max_results,
                "relevance_threshold": self.config.similarity_threshold,
            }

    def retrieve_memory_context(
        self, request: MemoryRetrievalRequest
    ) -> MemoryRetrievalResult:
        """Execute memory retrieval pipeline for a given user request."""
        if not self.config.enabled:
            return MemoryRetrievalResult(
                request_id=request.request_id,
                retrieval_status=RetrievalStatus.UNAVAILABLE,
                source_info="Retrieval service disabled in settings",
            )

        start_t = time.perf_counter()

        with self._lock:
            # 1. Trigger Policy Check
            should_ret, mode_used, reason = self.policy.should_retrieve(request)
            if not should_ret:
                self.metrics.record_request(
                    triggered=False,
                    skipped=True,
                    mode=mode_used.value,
                    latency_ms=(time.perf_counter() - start_t) * 1000.0,
                    candidates_found=0,
                    candidates_filtered=0,
                    selected_count=0,
                    context_chars=0,
                )
                return MemoryRetrievalResult(
                    request_id=request.request_id,
                    retrieval_status=RetrievalStatus.NO_RETRIEVAL_REQUIRED,
                    latency_ms=(time.perf_counter() - start_t) * 1000.0,
                    mode_used=mode_used,
                    source_info=f"Policy decision: {reason}",
                )

            # 2. Gather candidates from hybrid sources
            candidates: list[CandidateMemory] = []
            degraded = False

            # Source A: User Profile (Structured High-Confidence Preferences & Projects)
            if request.include_profile and self.user_profile_service:
                try:
                    profile = self.user_profile_service.get_profile()
                    for pref in profile.preferences.values():
                        candidates.append(
                            CandidateMemory(
                                memory_id=f"prof_pref_{pref.key}",
                                memory_type="PREFERENCE",
                                subject=pref.key,
                                content=str(pref.value),
                                source="USER_EXPLICIT" if pref.explicit else "DERIVED",
                                confidence=pref.confidence,
                                importance="HIGH" if pref.explicit else "MEDIUM",
                                created_at=pref.updated_at,
                                updated_at=pref.updated_at,
                                semantic_similarity=0.85,
                            )
                        )
                    for prj in profile.projects.values():
                        candidates.append(
                            CandidateMemory(
                                memory_id=f"prof_prj_{prj.name}",
                                memory_type="PROJECT",
                                subject=prj.name,
                                content=f"Project {prj.name}: path={prj.path}, role={prj.role}",
                                source="USER_EXPLICIT",
                                confidence=0.9,
                                importance="HIGH",
                                created_at=prj.updated_at,
                                updated_at=prj.updated_at,
                                semantic_similarity=0.80,
                            )
                        )
                except Exception as ex:  # noqa: BLE001
                    logger.warning(
                        f"MemoryRetrievalService: Profile fetch error ({ex})."
                    )
                    degraded = True

            # Source B: Structured Long-Term Memory
            if request.allow_structured_search and self.long_term_service:
                try:
                    lt_memories = self.long_term_service.list_memories()
                    for m in lt_memories:
                        candidates.append(
                            CandidateMemory(
                                memory_id=m.memory_id,
                                memory_type=str(
                                    m.memory_type.value
                                    if hasattr(m.memory_type, "value")
                                    else m.memory_type
                                ),
                                subject=m.subject,
                                content=m.content,
                                source=str(
                                    m.source.value
                                    if hasattr(m.source, "value")
                                    else m.source
                                ),
                                confidence=m.confidence,
                                importance=str(
                                    m.importance.value
                                    if hasattr(m.importance, "value")
                                    else m.importance
                                ),
                                created_at=m.created_at,
                                updated_at=m.updated_at,
                                expires_at=m.expires_at,
                                user_control_state=str(
                                    m.user_control_state.value
                                    if hasattr(m.user_control_state, "value")
                                    else m.user_control_state
                                ),
                                metadata=m.metadata or {},
                                semantic_similarity=0.50,
                            )
                        )
                    self.metrics.record_search(is_semantic=False)
                except Exception as ex:  # noqa: BLE001
                    logger.warning(
                        f"MemoryRetrievalService: Structured search error ({ex})."
                    )
                    degraded = True

            # Source C: Semantic Vector Memory Search
            if request.allow_semantic_search and self.semantic_service:
                try:
                    query_text = self.query_builder.build_query(
                        request.user_text,
                        current_intent=request.current_intent,
                        current_entities=request.current_entities,
                    )
                    if query_text:
                        hits = self.semantic_service.semantic_search(
                            query_text, top_k=self.config.max_candidates
                        )
                        if hits and self.long_term_service:
                            hit_map = {h.memory_id: h.similarity for h in hits}
                            # Batch fetch from SQLite
                            for m_id, sim in hit_map.items():
                                mem = self.long_term_service.get_memory(m_id)
                                if mem:
                                    candidates.append(
                                        CandidateMemory(
                                            memory_id=mem.memory_id,
                                            memory_type=str(
                                                mem.memory_type.value
                                                if hasattr(mem.memory_type, "value")
                                                else mem.memory_type
                                            ),
                                            subject=mem.subject,
                                            content=mem.content,
                                            source=str(
                                                mem.source.value
                                                if hasattr(mem.source, "value")
                                                else mem.source
                                            ),
                                            confidence=mem.confidence,
                                            importance=str(
                                                mem.importance.value
                                                if hasattr(mem.importance, "value")
                                                else mem.importance
                                            ),
                                            created_at=mem.created_at,
                                            updated_at=mem.updated_at,
                                            expires_at=mem.expires_at,
                                            user_control_state=str(
                                                mem.user_control_state.value
                                                if hasattr(
                                                    mem.user_control_state, "value"
                                                )
                                                else mem.user_control_state
                                            ),
                                            metadata=mem.metadata or {},
                                            semantic_similarity=sim,
                                        )
                                    )
                            self.metrics.record_search(is_semantic=True)
                except Exception as ex:  # noqa: BLE001
                    logger.warning(
                        f"MemoryRetrievalService: Semantic search error ({ex}). Using degraded structured fallback."
                    )
                    degraded = True

            total_found = len(candidates)

            # 3. Rank & Select Candidates
            ranked_memories = self.ranking_service.rank_candidates(
                candidates,
                current_entities=request.current_entities,
                relevance_threshold=request.relevance_threshold
                or self.config.similarity_threshold,
                max_results=request.max_results or self.config.max_results,
            )

            filtered_count = total_found - len(ranked_memories)

            # 4. Build Context Block
            context_text = self.context_builder.build_context_block(
                ranked_memories,
                max_chars=self.config.max_context_characters,
                max_memories=self.config.max_context_memories,
            )

            status = (
                RetrievalStatus.MEMORIES_FOUND
                if ranked_memories
                else RetrievalStatus.NO_RELEVANT_MEMORIES
            )
            if degraded and not ranked_memories:
                status = RetrievalStatus.DEGRADED

            elapsed_ms = (time.perf_counter() - start_t) * 1000.0

            self.metrics.record_request(
                triggered=True,
                skipped=False,
                mode=mode_used.value,
                latency_ms=elapsed_ms,
                candidates_found=total_found,
                candidates_filtered=filtered_count,
                selected_count=len(ranked_memories),
                context_chars=len(context_text),
                degraded=degraded,
            )

            return MemoryRetrievalResult(
                request_id=request.request_id,
                selected_memories=ranked_memories,
                total_candidates=total_found,
                filtered_candidates=filtered_count,
                selected_count=len(ranked_memories),
                retrieval_status=status,
                latency_ms=round(elapsed_ms, 2),
                context_text=context_text,
                context_characters=len(context_text),
                degraded_mode=degraded,
                mode_used=mode_used,
                source_info=f"Retrieved {len(ranked_memories)} memories in {elapsed_ms:.1f}ms",
            )
