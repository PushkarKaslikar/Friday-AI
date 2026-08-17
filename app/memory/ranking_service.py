"""Deterministic multi-factor ranking service scoring candidate memories.

Phase 5.6 - Memory Retrieval & Relevant Context Engine
"""

import math
import time
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from app.memory.retrieval_models import CandidateMemory, MemoryRetrievalConfig

SOURCE_TRUST_SCORES = {
    "USER_EXPLICIT": 1.0,
    "USER_CONFIRMED": 0.9,
    "SYSTEM": 0.8,
    "TOOL_DERIVED": 0.6,
    "DERIVED": 0.4,
}

IMPORTANCE_SCORES = {
    "CRITICAL": 1.0,
    "HIGH": 0.8,
    "MEDIUM": 0.5,
    "LOW": 0.2,
}


class MemoryRankingService:
    """Ranks candidate memories using a deterministic, multi-factor weighted scoring formula."""

    def __init__(self, config: "MemoryRetrievalConfig | None" = None) -> None:
        self.config = config

    def rank_candidates(
        self,
        candidates: list["CandidateMemory"],
        current_entities: list[str] | None = None,
        current_subject: str | None = None,
        relevance_threshold: float = 0.35,
        max_results: int = 5,
    ) -> list["CandidateMemory"]:
        """Filter, score, deduplicate, and rank candidate memories."""
        if not candidates:
            return []

        now = time.time()
        dedup_map: dict[str, CandidateMemory] = {}

        # 1. Deduplicate by memory_id and filter inactive/expired
        for c in candidates:
            if c.user_control_state != "ACTIVE":
                continue
            if c.expires_at and c.expires_at > 0 and c.expires_at < now:
                continue

            if (
                c.memory_id not in dedup_map
                or c.semantic_similarity > dedup_map[c.memory_id].semantic_similarity
            ):
                dedup_map[c.memory_id] = c

        valid_candidates = list(dedup_map.values())
        if not valid_candidates:
            return []

        # Read weights from config or use robust defaults
        w_sem = self.config.semantic_weight if self.config else 0.40
        w_rec = self.config.recency_weight if self.config else 0.15
        w_imp = self.config.importance_weight if self.config else 0.15
        w_cnf = self.config.confidence_weight if self.config else 0.15
        w_src = self.config.source_weight if self.config else 0.15
        w_ctx = self.config.context_match_weight if self.config else 0.10

        # Normalize weights so sum == 1.0
        total_w = w_sem + w_rec + w_imp + w_cnf + w_src + w_ctx
        if total_w > 0:
            w_sem /= total_w
            w_rec /= total_w
            w_imp /= total_w
            w_cnf /= total_w
            w_src /= total_w
            w_ctx /= total_w

        scored_candidates = []
        for c in valid_candidates:
            # 1. Semantic similarity score [0.0, 1.0]
            sem_score = max(0.0, min(1.0, c.semantic_similarity))

            # 2. Recency score with exponential decay (half-life ~ 30 days)
            age_seconds = max(0.0, now - (c.updated_at or c.created_at or now))
            age_days = age_seconds / 86400.0
            rec_score = math.exp(-0.023 * age_days)  # ~0.5 at 30 days

            # 3. Importance score
            imp_score = IMPORTANCE_SCORES.get(str(c.importance).upper(), 0.5)

            # 4. Confidence score
            cnf_score = max(0.0, min(1.0, c.confidence))

            # 5. Source trust score
            src_score = SOURCE_TRUST_SCORES.get(str(c.source).upper(), 0.5)

            # 6. Context match score
            ctx_score = 0.0
            if current_subject and current_subject.lower() in c.subject.lower():
                ctx_score += 0.6
            if current_entities:
                for ent in current_entities:
                    if (
                        ent.lower() in c.subject.lower()
                        or ent.lower() in c.content.lower()
                    ):
                        ctx_score += 0.4
                        break
            ctx_score = min(1.0, ctx_score)

            # Calculate final score
            final_score = (
                sem_score * w_sem
                + rec_score * w_rec
                + imp_score * w_imp
                + cnf_score * w_cnf
                + src_score * w_src
                + ctx_score * w_ctx
            )

            c.semantic_similarity = round(sem_score, 4)
            c.recency_score = round(rec_score, 4)
            c.importance_score = round(imp_score, 4)
            c.confidence_score = round(cnf_score, 4)
            c.source_score = round(src_score, 4)
            c.context_match_score = round(ctx_score, 4)
            c.final_score = round(final_score, 4)
            c.selection_reason = (
                f"sem={c.semantic_similarity}, rec={c.recency_score}, "
                f"imp={c.importance_score}, cnf={c.confidence_score}, "
                f"src={c.source_score}, ctx={c.context_match_score}"
            )

            if final_score >= relevance_threshold:
                scored_candidates.append(c)

        # Sort descending by final_score
        scored_candidates.sort(key=lambda x: x.final_score, reverse=True)
        ranked_selection = scored_candidates[:max_results]

        logger.debug(
            f"MemoryRankingService: Ranked {len(valid_candidates)} candidates -> {len(ranked_selection)} selected above threshold {relevance_threshold}."
        )
        return ranked_selection
